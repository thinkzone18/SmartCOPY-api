from fastapi import APIRouter, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime
from .db import licenses
from .utils import hash_key, make_expiry, is_expired
from .models import ValidateRequest, ValidateResponse, CreateLicenseRequest
from .config import settings
from .email_utils import send_license_email
import random, string

router = APIRouter()

API_KEY_HEADER = APIKeyHeader(name="X-Admin-Api-Key", auto_error=False)

# ✅ Admin Key Validation
def require_admin(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ✅ Validate license key (now supports 1 license = 1 PC)
@router.post("/validate", response_model=ValidateResponse)
async def validate(req: ValidateRequest, request: Request):
    """
    Validates a license key and binds it to a unique device_id (1PC rule).
    """
    key_hash = hash_key(req.license_key)
    device_id = getattr(req, "device_id", None)

    if not device_id:
        try:
            data = await request.json()
            device_id = data.get("device_id")
        except Exception:
            pass

    if not device_id:
        return ValidateResponse(valid=False, message="Missing device ID")

    # Find license record
    doc = licenses.find_one({"key_hash": key_hash, "active": True})
    if not doc:
        return ValidateResponse(valid=False, message="License not found or inactive")

    expiry = doc.get("expiry")
    if is_expired(expiry):
        return ValidateResponse(valid=False, expiry=expiry, message="License expired")

    # ✅ 1 License → 1 PC binding
    stored_device = doc.get("device_id")

    if not stored_device:
        # First activation → bind device ID
        licenses.update_one(
            {"_id": doc["_id"]},
            {"$set": {"device_id": device_id, "activated_on": datetime.utcnow().isoformat()}}
        )
        print(f"🔐 License {req.license_key} bound to device {device_id}")
        return ValidateResponse(valid=True, expiry=expiry, message="License activated on this device")

    if stored_device == device_id:
        # Same device re-activating
        return ValidateResponse(valid=True, expiry=expiry, message="License valid for this system")

    # ❌ Another device trying to use same key
    return ValidateResponse(valid=False, message="License already activated on another system")



# ✅ Admin: automatically generate a license key
@router.post("/admin/create", dependencies=[Depends(require_admin)])
def admin_create(req: CreateLicenseRequest):
    """
    Admin endpoint to create a new license key automatically.
    You only provide days_valid and optional metadata.
    """

    # 🔹 Generate random license key
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    license_key = f"SMARTCOPY-{'-'.join(parts)}"

    # 🔹 Compute hash for DB
    key_hash = hash_key(license_key)
    expiry = make_expiry(req.days_valid)

    # 🔹 Save to MongoDB
    licenses.insert_one({
        "key_hash": key_hash,
        "expiry": expiry,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": req.metadata or {},
        "active": True,
        "device_id": None,            # new
        "activated_on": None          # new
    })

    print(f"✅ License created automatically: {license_key}")

    # 🔹 Return license key to admin
    return {"ok": True, "license_key": license_key, "expiry": expiry}



# ✅ Gumroad webhook - creates license & emails buyer
@router.post("/webhook/gumroad")
async def gumroad_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Triggered when a user purchases SmartCOPY on Gumroad.
    Works with both test ping (form-data) and real purchases (JSON).
    """

    try:
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="ignore").strip()
        data = {}

        # Try parsing JSON
        if body_text.startswith("{"):
            try:
                data = await request.json()
            except Exception as e:
                print("⚠️ JSON parse failed, fallback to form:", e)

        # Fallback to form data
        if not data:
            try:
                form_data = await request.form()
                data = dict(form_data)
            except Exception as e:
                print("⚠️ Form parse failed:", e)

        print("🔔 Incoming Gumroad webhook payload:", data)

        purchaser_email = data.get("email") or data.get("purchaser_email")
        product_name = data.get("product_name", "SmartCOPY")

        if not purchaser_email:
            print("⚠️ Email missing in payload!")
            raise HTTPException(status_code=400, detail="Email missing in payload")

        # Generate new license key
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
        license_key = f"SMARTCOPY-{'-'.join(parts)}"

        # Save license in DB
        licenses.insert_one({
            "key_hash": hash_key(license_key),
            "expiry": make_expiry(365),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "email": purchaser_email,
                "product": product_name,
                "source": "gumroad"
            },
            "active": True,
            "device_id": None,
            "activated_on": None
        })

        # Send email asynchronously via Brevo
        background_tasks.add_task(send_license_email, purchaser_email, license_key)
        print(f"✅ License created and emailed to {purchaser_email}: {license_key}")

        return {"ok": True, "license_key": license_key}

    except Exception as e:
        print("❌ Webhook error:", e)
        raise HTTPException(status_code=500, detail=str(e))



# ✅ Optional: Reset a license (Admin only)
@router.post("/admin/reset-license", dependencies=[Depends(require_admin)])
def reset_license(req: dict):
    """
    Admin-only route to reset a license (unbind device).
    """
    key_hash = hash_key(req.get("license_key"))
    result = licenses.update_one(
        {"key_hash": key_hash},
        {"$set": {"device_id": None, "activated_on": None}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="License not found")

    return {"ok": True, "message": "License reset successfully"}

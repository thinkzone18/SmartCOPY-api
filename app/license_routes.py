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

def require_admin(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ✅ Validate license key endpoint
@router.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest):
    key_hash = hash_key(req.license_key)
    doc = licenses.find_one({"key_hash": key_hash, "active": True})
    if not doc:
        return ValidateResponse(valid=False, message="License not found or inactive")

    expiry = doc.get("expiry")
    if is_expired(expiry):
        return ValidateResponse(valid=False, expiry=expiry, message="License expired")

    return ValidateResponse(valid=True, expiry=expiry, message="License valid")



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
        "active": True
    })

    print(f"✅ License created automatically: {license_key}")

    # 🔹 Return license key to admin
    return {"ok": True, "license_key": license_key, "expiry": expiry}



# ✅ Gumroad webhook - flexible version
@router.post("/webhook/gumroad")
async def gumroad_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Triggered when a user purchases SmartCOPY on Gumroad.
    Works with both test ping (form-data) and real purchases (JSON).
    """

    try:
        # Read raw body safely
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="ignore").strip()

        data = {}

        # Try parsing as JSON first
        if body_text.startswith("{"):
            try:
                data = await request.json()
            except Exception as e:
                print("⚠️ JSON parse failed, fallback to form:", e)

        # If not JSON, try form
        if not data:
            try:
                form_data = await request.form()
                data = dict(form_data)
            except Exception as e:
                print("⚠️ Form parse failed:", e)

        print("🔔 Incoming Gumroad webhook payload:", data)

        # Extract buyer email
        purchaser_email = data.get("email") or data.get("purchaser_email")
        product_name = data.get("product_name", "SmartCOPY")

        if not purchaser_email:
            print("⚠️ Email missing in payload!")
            raise HTTPException(status_code=400, detail="Email missing in payload")

        # Generate license key
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
        license_key = f"SMARTCOPY-{'-'.join(parts)}"

        # Save license in MongoDB
        licenses.insert_one({
            "key_hash": hash_key(license_key),
            "expiry": make_expiry(365),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "email": purchaser_email,
                "product": product_name,
                "source": "gumroad"
            },
            "active": True
        })

        # Send email asynchronously
        background_tasks.add_task(send_license_email, purchaser_email, license_key)
        print(f"✅ License created and emailed to {purchaser_email}: {license_key}")

        return {"ok": True, "license_key": license_key}

    except Exception as e:
        print("❌ Webhook error:", e)
        raise HTTPException(status_code=500, detail=str(e))


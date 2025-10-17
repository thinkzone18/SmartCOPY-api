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


# ✅ Admin: manually create a license
@router.post("/admin/create", dependencies=[Depends(require_admin)])
def admin_create(req: CreateLicenseRequest):
    key_hash = hash_key(req.license_key)
    expiry = make_expiry(req.days_valid)
    licenses.insert_one({
        "key_hash": key_hash,
        "expiry": expiry,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": req.metadata or {},
        "active": True
    })
    return {"ok": True, "expiry": expiry}


# ✅ Gumroad webhook - flexible version
@router.post("/webhook/gumroad")
async def gumroad_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Triggered when a user purchases SmartCOPY on Gumroad.
    Works with both form-data and JSON payloads.
    """

    try:
        # Gumroad test ping → form data
        try:
            data = await request.form()
        except:
            data = await request.json()

        # Convert to dict (form returns FormData object)
        data = dict(data)
        print("🔔 Incoming Gumroad webhook:", data)

        purchaser_email = data.get("email") or data.get("purchaser_email")
        product_name = data.get("product_name", "SmartCOPY Pro")

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
            "metadata": {"email": purchaser_email, "product": product_name, "source": "gumroad"},
            "active": True
        })

        # Send email asynchronously
        background_tasks.add_task(send_license_email, purchaser_email, license_key)
        print(f"✅ License created for {purchaser_email}: {license_key}")

        return {"ok": True, "license_key": license_key}

    except Exception as e:
        print("❌ Webhook error:", e)
        raise HTTPException(status_code=500, detail=str(e))

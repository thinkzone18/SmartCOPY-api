from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime
from .db import licenses
from .utils import hash_key, make_expiry, is_expired
from .models import ValidateRequest, ValidateResponse, CreateLicenseRequest, GumroadWebhook  # ✅ include GumroadWebhook here
from .config import settings
from .email_utils import send_license_email
import hashlib, hmac, random, string


router = APIRouter()

API_KEY_HEADER = APIKeyHeader(name="X-Admin-Api-Key", auto_error=False)

def require_admin(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

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

@router.post("/webhook/gumroad")
async def gumroad_webhook(payload: GumroadWebhook):
    """
    Triggered when a user purchases SmartCOPY on Gumroad.
    Creates a 1-year license and emails it to the purchaser.
    """
    data = payload.dict(exclude_none=True)
    purchaser_email = data.get("email") or data.get("purchaser_email")
    if not purchaser_email:
        raise HTTPException(status_code=400, detail="Email missing in payload")

    # Generate random license key
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(random.choices(chars, k=4)) for _ in range(3)]
    license_key = f"SMARTCOPY-{'-'.join(parts)}"

    # Save license in MongoDB
    licenses.insert_one({
        "key_hash": hash_key(license_key),
        "expiry": make_expiry(365),
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {"email": purchaser_email, "source": "gumroad"},
        "active": True
    })

    # Send license email
    try:
        send_license_email(purchaser_email, license_key)
    except Exception as e:
        print("⚠️ Email sending failed:", e)

    return {"ok": True, "license_key": license_key}


from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime
from .db import licenses
from .utils import hash_key, make_expiry, is_expired
from .models import ValidateRequest, ValidateResponse, CreateLicenseRequest
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
async def gumroad_webhook(request: Request):
    body = await request.body()
    payload = await request.json()
    secret = settings.GUMROAD_SECRET
    if secret:
        sig_header = request.headers.get("Gumroad-Signature", "")
        computed = hashlib.sha256(secret.encode() + body).hexdigest()
        if not hmac.compare_digest(computed, sig_header):
            raise HTTPException(status_code=403, detail="Invalid signature")

    purchaser_email = payload.get("email") or payload.get("purchaser_email")
    if not purchaser_email:
        raise HTTPException(status_code=400, detail="Email missing in payload")

    def generate_license():
        parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
        return f"SMARTCOPY-{'-'.join(parts)}"

    key = generate_license()
    licenses.insert_one({
        "key_hash": hash_key(key),
        "expiry": make_expiry(365),
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {"email": purchaser_email, "source": "gumroad"},
        "active": True
    })

    send_license_email(purchaser_email, key)
    return {"ok": True, "license_key": key}

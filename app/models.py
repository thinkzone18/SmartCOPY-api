from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Any


# ============================================================
# ✅ Validation Request/Response Models
# ============================================================
class ValidateRequest(BaseModel):
    license_key: str
    device_id: Optional[str] = None  # 🔹 New: unique system identifier


class ValidateResponse(BaseModel):
    valid: bool
    expiry: Optional[str] = None
    message: Optional[str] = None


# ============================================================
# ✅ Admin Create License Request
# ============================================================
class CreateLicenseRequest(BaseModel):
    # We now auto-generate the license key, so this field is optional
    license_key: Optional[str] = None
    days_valid: int = Field(default=365, ge=1)
    metadata: Optional[dict] = None


# ============================================================
# ✅ License Document (MongoDB schema)
# ============================================================
class LicenseDocument(BaseModel):
    key_hash: str
    expiry: str
    created_at: str
    metadata: Optional[dict] = None
    active: bool = True
    device_id: Optional[str] = None      # 🔹 New field: system binding
    activated_on: Optional[str] = None   # 🔹 New field: activation date


# ============================================================
# ✅ Gumroad Webhook Payload
# ============================================================
class GumroadWebhook(BaseModel):
    email: Optional[EmailStr] = None
    purchaser_email: Optional[EmailStr] = None
    product_name: Optional[str] = None
    purchaser_name: Optional[str] = None
    sale_id: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    test: Optional[str] = None

from pydantic import BaseModel, Field
from typing import Optional

class ValidateRequest(BaseModel):
    license_key: str

class ValidateResponse(BaseModel):
    valid: bool
    expiry: Optional[str] = None
    message: Optional[str] = None

class CreateLicenseRequest(BaseModel):
    license_key: str
    days_valid: int = Field(default=365, ge=1)
    metadata: Optional[dict] = None

class LicenseDocument(BaseModel):
    key_hash: str
    expiry: str
    created_at: str
    metadata: Optional[dict] = None
    active: bool = True

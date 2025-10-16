from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.security.api_key import APIKeyHeader
from datetime import datetime
from .config import settings
from .db import licenses
from .utils import hash_key, make_expiry, is_expired
from .models import ValidateRequest, ValidateResponse, CreateLicenseRequest
import hashlib
import hmac
import os
from pyngrok import ngrok  # ✅ auto-tunnel for local tests

app = FastAPI(title="SmartCOPY License API")

API_KEY_HEADER = APIKeyHeader(name="X-Admin-Api-Key", auto_error=False)

# ---------------------------
# 🔐 ADMIN AUTH
# ---------------------------
def require_admin(api_key: str = Depends(API_KEY_HEADER)):
    if not api_key or api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ---------------------------
# 🧠 VALIDATE LICENSE
# ---------------------------
@app.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest):
    key_hash = hash_key(req.license_key)
    doc = licenses.find_one({"key_hash": key_hash, "active": True})
    if not doc:
        return ValidateResponse(valid=False, message="License not found or inactive")

    expiry = doc.get("expiry")
    if is_expired(expiry):
        return ValidateResponse(valid=False, expiry=expiry, message="License expired")

    return ValidateResponse(valid=True, expiry=expiry, message="License valid")


# ---------------------------
# 🧩 CREATE LICENSE (Admin)
# ---------------------------
@app.post("/admin/create", dependencies=[Depends(require_admin)])
def admin_create(req: CreateLicenseRequest):
    key_hash = hash_key(req.license_key)
    expiry = make_expiry(req.days_valid)
    doc = {
        "key_hash": key_hash,
        "expiry": expiry,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": req.metadata or {},
        "active": True,
    }
    licenses.insert_one(doc)
    return {"ok": True, "expiry": expiry}


# ---------------------------
# 🚫 REVOKE LICENSE
# ---------------------------
@app.post("/admin/revoke", dependencies=[Depends(require_admin)])
def admin_revoke(payload: dict):
    if "license_key" in payload:
        key_hash = hash_key(payload["license_key"])
    elif "key_hash" in payload:
        key_hash = payload["key_hash"]
    else:
        raise HTTPException(status_code=400, detail="license_key or key_hash required")

    res = licenses.update_one({"key_hash": key_hash}, {"$set": {"active": False}})
    return {"matched": res.matched_count, "modified": res.modified_count}


# ---------------------------
# 📋 LIST LICENSES
# ---------------------------
@app.get("/admin/list", dependencies=[Depends(require_admin)])
def admin_list(limit: int = 50):
    docs = list(licenses.find().sort("created_at", -1).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"count": len(docs), "licenses": docs}


# ---------------------------
# 🧾 GUMROAD WEBHOOK TEST
# ---------------------------
@app.post("/webhook/gumroad")
async def gumroad_webhook(request: Request):
    """
    Local testing version — no signature validation yet.
    Prints received webhook payload in console.
    """
    payload = await request.json()
    print("\n🧩 Received Gumroad webhook (test mode):")
    print(payload)
    return {"ok": True, "message": "Webhook received (local test)"}


# ---------------------------
# 🚀 AUTO NGROK (Local Mode)
# ---------------------------
@app.on_event("startup")
def start_ngrok():
    """Start ngrok automatically for local FastAPI testing"""
    if os.environ.get("RUN_ENV") != "production":
        port = 8000
        public_url = ngrok.connect(port).public_url
        print("\n===============================")
        print(f"🚀 SmartCOPY API running locally on: http://127.0.0.1:{port}")
        print(f"🌍 Public ngrok URL: {public_url}")
        print(f"🔗 Webhook endpoint: {public_url}/webhook/gumroad")
        print("===============================\n")

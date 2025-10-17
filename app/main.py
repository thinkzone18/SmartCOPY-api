from fastapi import FastAPI
from .license_routes import router

app = FastAPI(title="SmartCOPY License API")
app.include_router(router)

# Include your main routes
app.include_router(router)

# 👇 Add this route to confirm service status
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "SmartCOPY License API is running",
        "docs": "/docs"
    }
from fastapi import FastAPI
from .license_routes import router


app = FastAPI(title="SmartCOPY License API")

# Include routes once (duplicate not needed)
app.include_router(router)

# Health check route for Render
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "SmartCOPY License API is running",
        "docs": "/docs"
    }
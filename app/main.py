from fastapi import FastAPI
from .license_routes import router

app = FastAPI(title="SmartCOPY License API")
app.include_router(router)

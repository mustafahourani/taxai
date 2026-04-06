from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.routers import attestation, form1040

app = FastAPI(title="TaxAI", description="Privacy-preserving AI tax filing via TEE + E2EE")

app.include_router(attestation.router)
app.include_router(form1040.router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))

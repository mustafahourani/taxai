import json
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import Response

from app.services.form1040_engine import compute_form_1040
from app.services.ai import review_tax_return, extract_documents
from app.services.pdf_generator import generate_form_1040_pdf

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent / "data"


@router.get("/api/mock-taxpayer")
async def get_mock_taxpayer():
    with open(DATA_DIR / "mock_taxpayer.json") as f:
        return json.load(f)


@router.post("/api/extract-documents")
async def extract_docs(
    files: list[UploadFile] = File(None),
    use_demo: bool = Form(False),
    demo_docs: str = Form(""),
):
    """Upload W-2, 1098-E, etc. documents and let AI extract all tax data."""
    if use_demo or not files:
        return _demo_extract(demo_docs)

    # Real document extraction via AI
    file_contents = []
    for f in files:
        content = await f.read()
        file_contents.append({
            "filename": f.filename,
            "content_type": f.content_type,
            "size": len(content),
            "content": content,
        })

    return await extract_documents(file_contents)


def _demo_extract(demo_docs: str) -> dict:
    """Return mock extraction based on which demo docs were selected."""
    with open(DATA_DIR / "mock_taxpayer.json") as f:
        data = json.load(f)

    selected = demo_docs.split(",") if demo_docs else ["w2", "1098e"]
    extractions = []

    if "w2" not in selected:
        # No W-2 — zero out income (unlikely but handle it)
        data["w2s"] = []

    if "1098e" not in selected:
        # No 1098-E — remove student loan interest
        data["student_loan_interest"] = 0

    if "w2" in selected:
        extractions.append({
            "document_type": "W-2",
            "employer": "University of Pittsburgh",
            "confidence": "high",
            "fields_extracted": 10,
        })

    if "1098e" in selected:
        extractions.append({
            "document_type": "1098-E",
            "employer": "FedLoan Servicing (PHEAA)",
            "confidence": "high",
            "fields_extracted": 2,
        })

    return {
        "extracted": data,
        "documents_processed": len(extractions),
        "source": "demo",
        "extractions": extractions,
    }


@router.post("/api/compute-1040")
async def compute_1040(request: Request):
    data = await request.json()
    result = compute_form_1040(data)
    return result


@router.post("/api/review-1040")
async def review_1040(request: Request):
    data = await request.json()
    suggestions = await review_tax_return(data)
    return {"suggestions": suggestions}


@router.post("/api/1040-pdf")
async def download_1040_pdf(request: Request):
    data = await request.json()
    result = compute_form_1040(data)
    pdf_bytes = generate_form_1040_pdf(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=form_1040_draft.pdf"},
    )

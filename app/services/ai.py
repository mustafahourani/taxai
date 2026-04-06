"""AI service using Anthropic Claude for document extraction and tax review."""

import json
import base64
from pathlib import Path

from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, USE_MOCK_AI


def _strip_markdown_json(text: str) -> str:
    """Strip markdown code fences from JSON responses."""
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return text


TAX_REVIEW_PROMPT = """You are a tax review assistant. You review a completed Form 1040 tax return and provide helpful suggestions.

Your job:
1. Look for commonly missed deductions or credits the taxpayer might qualify for
2. Flag any obvious issues or inconsistencies
3. Suggest tax-saving strategies for next year
4. Keep suggestions practical and specific to their situation

RULES:
- Be conservative — never suggest anything aggressive or questionable
- Only suggest things that are clearly applicable based on the data provided
- Keep each suggestion to 1-2 sentences
- Return exactly 3-5 suggestions
- Do NOT suggest things already reflected in the return

OUTPUT FORMAT:
Return a JSON array of objects, each with:
- "type": "suggestion" | "next_year" | "flag"
- "title": Short title (5-8 words)
- "detail": One sentence explanation
- "potential_savings": Estimated dollar amount if applicable, or null

Return ONLY valid JSON. No markdown wrapping."""


EXTRACT_PROMPT = """You are a tax document extraction engine. You read uploaded tax documents (W-2, 1099-INT, 1099-DIV, 1099-NEC, 1098, etc.) and extract structured data.

For a W-2, extract:
- employer name (Box c)
- employer EIN (Box b)
- wages (Box 1)
- federal_withheld (Box 2)
- ss_wages (Box 3)
- ss_withheld (Box 4)
- medicare_wages (Box 5)
- medicare_withheld (Box 6)
- state, state_wages, state_withheld (Boxes 15-17)
- employee name, SSN, address

For a 1099-INT, extract:
- payer name
- interest_income (Box 1)

For a 1099-DIV, extract:
- payer name
- ordinary_dividends (Box 1a)

Return a JSON object with this exact structure:
{
  "filing_status": "single",
  "first_name": "",
  "last_name": "",
  "ssn": "",
  "address": "",
  "dependents": [],
  "w2s": [{"employer": "", "ein": "", "wages": 0, "federal_withheld": 0, "ss_wages": 0, "ss_withheld": 0, "medicare_wages": 0, "medicare_withheld": 0, "state": "", "state_wages": 0, "state_withheld": 0}],
  "interest_income": 0,
  "dividend_income": 0,
  "other_income": 0,
  "adjustments": 0,
  "use_standard_deduction": true,
  "itemized_deductions": 0,
  "digital_assets": false
}

Return ONLY valid JSON. No markdown wrapping."""


MOCK_REVIEW = [
    {
        "type": "suggestion",
        "title": "Consider contributing to a Traditional IRA",
        "detail": "You can deduct up to $7,000 in Traditional IRA contributions before the April 15 deadline, reducing your taxable income and saving approximately $1,540 at your marginal rate.",
        "potential_savings": 1540,
    },
    {
        "type": "suggestion",
        "title": "Max out your HSA if eligible",
        "detail": "If you have a high-deductible health plan, HSA contributions up to $4,300 are tax-deductible and reduce your AGI. Contributions can be made until April 15.",
        "potential_savings": 946,
    },
    {
        "type": "next_year",
        "title": "Adjust your W-4 withholding",
        "detail": "Your employer withheld more than your actual tax liability, resulting in a refund. Consider adjusting your W-4 to keep more in each paycheck instead of giving the IRS an interest-free loan.",
        "potential_savings": None,
    },
]


async def extract_documents(file_contents: list[dict]) -> dict:
    """Extract tax data from uploaded documents using Claude."""
    if USE_MOCK_AI:
        return _mock_extract()
    return await _claude_extract(file_contents)


async def review_tax_return(form_1040_data: dict) -> list[dict]:
    """Have Claude review a completed 1040 and suggest improvements."""
    if USE_MOCK_AI:
        return MOCK_REVIEW
    return await _claude_review(form_1040_data)


def _mock_extract() -> dict:
    """Return mock extraction for demo purposes."""
    data_dir = Path(__file__).parent.parent / "data"
    with open(data_dir / "mock_taxpayer.json") as f:
        data = json.load(f)
    return {
        "extracted": data,
        "documents_processed": 2,
        "source": "mock_ai",
        "extractions": [
            {
                "document_type": "W-2",
                "employer": "University of Pittsburgh",
                "confidence": "high",
                "fields_extracted": 10,
            },
            {
                "document_type": "1098-E",
                "employer": "FedLoan Servicing (PHEAA)",
                "confidence": "high",
                "fields_extracted": 2,
            },
        ],
    }


async def _claude_extract(file_contents: list[dict]) -> dict:
    """Use Claude to extract data from uploaded tax documents."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Build message content with document images/PDFs
    content = []
    for fc in file_contents:
        # Determine media type
        ct = fc.get("content_type", "")
        if "pdf" in ct:
            media_type = "application/pdf"
        elif "png" in ct:
            media_type = "image/png"
        elif "jpeg" in ct or "jpg" in ct:
            media_type = "image/jpeg"
        else:
            media_type = "application/pdf"

        # Encode file content as base64
        b64_data = base64.b64encode(fc["content"]).decode("utf-8")

        if media_type == "application/pdf":
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_data,
                },
            })
        else:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_data,
                },
            })

    content.append({
        "type": "text",
        "text": "Extract all tax data from the uploaded document(s). Return the structured JSON as specified.",
    })

    response = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=EXTRACT_PROMPT,
        messages=[{"role": "user", "content": content}],
        temperature=0.0,
    )

    response_text = _strip_markdown_json(response.content[0].text.strip())
    extracted = json.loads(response_text)

    # Build extraction summary
    extractions = []
    for w2 in extracted.get("w2s", []):
        extractions.append({
            "document_type": "W-2",
            "employer": w2.get("employer", "Unknown"),
            "confidence": "high",
            "fields_extracted": sum(1 for v in w2.values() if v),
        })

    if not extractions:
        extractions = [{"document_type": "unknown", "confidence": "medium", "fields_extracted": 0}]

    return {
        "extracted": extracted,
        "documents_processed": len(file_contents),
        "source": "claude",
        "extractions": extractions,
    }


async def _claude_review(form_data: dict) -> list[dict]:
    """Use Claude to review a completed 1040 and suggest improvements."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    summary = json.dumps({
        "filing_status": form_data.get("filing_status_name", ""),
        "wages": form_data["line_items"]["1a_wages"],
        "interest": form_data["line_items"]["2b_interest"],
        "agi": form_data["line_items"]["11_agi"],
        "deduction_type": form_data["line_items"]["12_deduction_type"],
        "deduction_amount": form_data["line_items"]["12_deduction"],
        "taxable_income": form_data["line_items"]["14_taxable_income"],
        "total_tax": form_data["line_items"]["24_total_tax"],
        "federal_withheld": form_data["line_items"]["25a_federal_withheld"],
        "refund": form_data["summary"]["refund"],
        "owed": form_data["summary"]["owed"],
        "effective_rate": form_data["summary"]["effective_rate"],
        "dependents": form_data.get("qualifying_children", 0),
    }, indent=2)

    response = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=TAX_REVIEW_PROMPT,
        messages=[{
            "role": "user",
            "content": "Review this completed Form 1040 and suggest improvements:\n\n" + summary,
        }],
        temperature=0.3,
    )

    response_text = _strip_markdown_json(response.content[0].text.strip())
    return json.loads(response_text)

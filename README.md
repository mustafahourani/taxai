# TaxAI

Privacy-preserving AI tax filing. Upload your W-2 and tax documents, get a completed IRS Form 1040 back. Your data is processed inside a hardware-encrypted enclave. Nobody sees it.

---

## What It Does

1. You upload your W-2, 1098-E, or other tax documents
2. AI extracts all the numbers (wages, withholding, interest, etc.)
3. A deterministic tax engine computes your Form 1040 using 2025 federal tax brackets
4. The engine optimizes your return (standard vs. itemized deduction, student loan interest deduction, child tax credit)
5. You download a filled official IRS Form 1040 PDF

The entire process runs inside a Trusted Execution Environment (TEE) on EigenCompute. The server operator cannot read the enclave's memory. Nothing is stored.

---

## Architecture

```
User's Browser
    |
    | HTTPS
    |
    v
+------------------------------------------+
|  EigenCompute TEE (AMD SEV-SNP)          |
|                                          |
|  TaxAI Application                       |
|  - FastAPI backend + static frontend     |
|  - Form 1040 tax engine (pure math)      |
|  - 2025 federal tax brackets             |
|  - PDF form filler (pypdf)               |
|                                          |
|  AI calls (document extraction + review) |
|  -> Claude Opus 4.6 via Anthropic API    |
+------------------------------------------+
```

**What uses AI:**
- Document extraction (reading W-2/1098-E PDFs)
- Tax review and suggestions

**What does NOT use AI:**
- Tax computation (deterministic bracket calculation)
- Deduction optimization (compare two numbers, pick the larger)
- PDF generation (field mapping)

---

## Features

- Reads W-2 and 1098-E documents via AI vision
- Computes all Form 1040 line items (Lines 1a through 37)
- Correct 2025 tax brackets for all filing statuses (Single, MFJ, MFS, HOH)
- Standard deduction: $15,750 (Single), $31,500 (MFJ), $23,625 (HOH)
- Student loan interest deduction (up to $2,500, from 1098-E)
- Child tax credit ($2,000 per qualifying child)
- Fills the real IRS Form 1040 PDF (not a custom form)
- Filing status checkbox (Single)
- Digital assets Yes/No checkbox
- Optimization tab showing every decision the AI made and dollar savings
- Suggestions tab with actionable tax-saving tips
- Privacy section explaining TEE, data at rest, data in transit, and on-chain verification
- Demo mode with sample W-2 and 1098-E documents
- Deployed on EigenCompute inside AMD SEV-SNP TEE

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.11 |
| Framework | FastAPI |
| Frontend | Static HTML + vanilla JS + CSS |
| AI | Claude Opus 4.6 (Anthropic API) |
| PDF | pypdf (fills official IRS Form 1040) |
| Compute | EigenCompute (AMD SEV-SNP TEE) |
| Container | Docker |

---

## Project Structure

```
TaxAI/
  Dockerfile
  requirements.txt
  .env                          # Your API keys (not committed)
  .gitignore
  TAXAI_SPEC.md                 # Full technical spec
  README.md
  app/
    main.py                     # FastAPI entry point
    config.py                   # Loads env vars
    static/
      index.html                # Single-page UI
      style.css
      app.js
    routers/
      attestation.py            # TEE attestation endpoint
      form1040.py               # Document extraction, tax computation, PDF endpoints
    services/
      ai.py                     # Claude AI client (extraction + review)
      form1040_engine.py        # Deterministic tax computation
      pdf_generator.py          # Fills IRS Form 1040 PDF
    data/
      tax_tables.py             # 2025 federal tax brackets
      mock_taxpayer.json        # Demo data
      f1040.pdf                 # Official IRS Form 1040 template
      sample_w2.pdf             # Sample W-2 document
      sample_1098e.pdf          # Sample 1098-E document
```

---

## Run Locally

### Prerequisites
- Python 3.9+
- An Anthropic API key (for real document extraction)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/TaxAI.git
cd TaxAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

Create a `.env` file:

```
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-opus-4-6
USE_MOCK_AI=false
EIGENCOMPUTE_TEE=false
```

Set `USE_MOCK_AI=true` to run without an API key (uses hardcoded demo data).

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000

---

## Deploy to EigenCompute

### Prerequisites
- Docker Desktop
- Node.js (for ecloud CLI)
- Docker Hub account
- EigenCompute account with Sepolia testnet ETH

### Steps

1. Install the CLI:
```bash
npm install -g @layr-labs/ecloud-cli
```

2. Authenticate:
```bash
ecloud auth generate --store
ecloud compute env set sepolia
ecloud billing subscribe
```

3. Fund your wallet with Sepolia ETH from https://cloud.google.com/application/web3/faucet/ethereum/sepolia

4. Update the Dockerfile with your API key:
```dockerfile
ENV ANTHROPIC_API_KEY=your-key-here
ENV USE_MOCK_AI=false
ENV EIGENCOMPUTE_TEE=true
```

5. Build for x86 and push:
```bash
docker buildx build --platform linux/amd64 --no-cache --push -t YOUR_DOCKERHUB/taxai:latest .
```

6. Deploy:
```bash
ecloud compute app deploy
```
Select "Deploy existing image from registry" and enter your image reference.

7. Get your app URL:
```bash
ecloud compute app info
```

---

## Tax Computation Verification

The tax engine produces mathematically verified results. For the sample W-2 (Elizabeth A Darling, University of Pittsburgh):

| Line | Value | Source |
|------|-------|--------|
| 1a Wages | $44,629.35 | W-2 Box 1 |
| 10 Adjustments | $1,847.32 | 1098-E Box 1 (student loan interest) |
| 11a AGI | $42,782.03 | $44,629.35 - $1,847.32 |
| 12e Deduction | $15,750.00 | 2025 single standard deduction |
| 15 Taxable income | $27,032.03 | AGI - deduction |
| 16 Tax | $3,005.34 | 10% on $11,925 + 12% on $15,107.03 |
| 25a Withheld | $7,631.62 | W-2 Box 2 |
| 34 Refund | $4,626.28 | $7,631.62 - $3,005.34 |

Effective tax rate: 6.7%

---

## Privacy Model

**What is private (TEE protects):**
- Application compute runs inside AMD SEV-SNP hardware enclave
- Server operator cannot read enclave memory
- No data stored persistently (stateless)
- Deployment verified on-chain

**What is NOT private in this PoC:**
- AI inference calls go to Anthropic (Claude API sees prompts)
- To make inference private, swap Claude for Venice AI E2EE (end-to-end encrypted inference inside hardware enclaves)

---

## Taking It Further: Private Inference

This PoC uses Claude Opus 4.6 for document extraction and tax review. Claude is best-in-class for these tasks, but the prompts (which contain your W-2 data) are sent to Anthropic's servers in plaintext. The compute is private (TEE), but the inference is not.

There are two paths to close this gap:

**Option 1: Venice AI E2EE**

Venice AI offers end-to-end encrypted inference. Prompts are encrypted before leaving the EigenCompute TEE and only decrypted inside Venice's hardware enclave. Venice cannot see the plaintext data at any point. This creates a two-TEE chain where your financial data never exists in readable form outside of hardware enclaves. Venice supports open-source models (Llama, Qwen, Gemma) through their E2EE API.

- Venice AI: https://venice.ai/
- Venice E2EE: https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai

**Option 2: Run open-source models locally inside the TEE**

Instead of calling an external API, run inference directly inside the EigenCompute enclave. Download an open-source model (Llama 3, Qwen, Mistral) and run it locally. This eliminates external API calls entirely. All extraction and review happens inside the same TEE as the tax computation. No data ever leaves the enclave. This requires a larger instance (GPU or high-memory CPU for quantized models) but provides the strongest privacy guarantee since there is no second party involved at all.

The code is already structured for either swap. The AI client in `app/services/ai.py` has a clean interface. Replace the `_claude_extract` and `_claude_review` functions with either Venice API calls or local model inference and the privacy story is complete.

- EigenCompute: https://docs.eigencloud.xyz/eigencompute/get-started/eigencompute-overview

---

## License

This is a proof of concept. Not for production tax filing. Consult a qualified tax professional.

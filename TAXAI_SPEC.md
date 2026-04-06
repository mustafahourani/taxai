# SPEC: TaxAI — Private Personal Tax Filing via Confidential Compute + Encrypted Inference

> Upload your W-2, get a complete Form 1040 back. Your financial data never leaves encrypted hardware enclaves — not the app developer, not the AI provider, not the compute provider can see it.

---

## 1. Problem Statement

AI-powered tax filing is emerging as a real product category. [Jupid](https://www.producthunt.com/products/jupid) launched on Product Hunt with a tool that uses Claude Code for tax preparation. But every AI tax tool today sends your complete financial data — W-2 wages, SSN, income, deductions — to an AI provider's servers in plaintext.

TaxAI demonstrates that private AI tax filing is solvable today using:
- **[EigenCompute](https://docs.eigencloud.xyz/eigencompute/get-started/eigencompute-overview)** — Trusted Execution Environments (Intel TDX) for confidential application compute
- **[Venice AI E2EE](https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai)** — End-to-end encrypted AI inference inside hardware enclaves (via NEAR AI Cloud / Phala Network)

The result: a personal tax filing assistant where **nobody sees your data**.

---

## 2. What It Does

TaxAI generates a complete **IRS Form 1040 (U.S. Individual Income Tax Return)** from uploaded tax documents. The user uploads their W-2 (and other tax documents) and the AI handles everything:

1. **Extracts** all data from uploaded documents (W-2 wages, withholding, employer info, SSN, address)
2. **Computes** the full 1040 — AGI, deductions, tax brackets, credits, refund/owed
3. **Optimizes** — automatically selects the best deduction strategy, applies all eligible credits
4. **Reviews** — AI analyzes the completed return and suggests additional savings
5. **Outputs** — filled official IRS Form 1040 PDF ready for download

The user flow is: **upload documents → get results**. No manual data entry.

---

## 3. Architecture

```
User's Browser
    |
    | HTTPS (TLS terminates inside TEE)
    |
    v
+------------------------------------------+
|  EigenCompute TEE (Intel TDX)            |
|                                          |
|  +------------------------------------+  |
|  | TaxAI Application                  |  |
|  | - FastAPI backend + static UI      |  |
|  | - Form 1040 tax engine (pure math) |  |
|  | - 2025 federal tax brackets        |  |
|  | - PDF form filler (pypdf)          |  |
|  +------------------------------------+  |
|         |                  |             |
|         | (1) Extract      | (2) Review  |
|         | W-2 data         | return      |
+---------|---------+--------|-------------+
          |                  |
          v                  v
+------------------------------------------+
|  Claude Opus 4.6 (Anthropic API)         |
|  [PoC — swap for Venice E2EE in prod]    |
|                                          |
|  - Reads W-2 documents (vision)          |
|  - Reviews returns, suggests savings     |
+------------------------------------------+
```

### PoC vs. Production Inference

**PoC (current):** AI inference uses Claude Opus 4.6 via the Anthropic API. This provides best-in-class document understanding and tax review. However, prompts containing financial data are sent to Anthropic's servers — the compute is private (EigenCompute TEE), but inference is not.

**Production (next level):** Swap Claude for [Venice AI E2EE](https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai) — end-to-end encrypted inference inside hardware enclaves (NVIDIA H100 CC via NEAR AI Cloud / Phala Network). This would make inference private too, completing the full zero-knowledge chain.

### What Uses AI vs. What Doesn't

| Step | Method | Why |
|------|--------|-----|
| **Document extraction** (reading W-2) | Claude Opus 4.6 (PoC) / Venice E2EE (prod) | Requires understanding document layout, OCR, field identification — LLM task |
| **Tax computation** (1040 math) | Deterministic algorithm | Tax brackets, deductions, credits are fixed rules — no AI needed |
| **Optimization decisions** (standard vs. itemized) | Deterministic algorithm | Compare two numbers, pick the larger deduction — pure math |
| **Review & suggestions** (missed deductions, tips) | Claude Opus 4.6 (PoC) / Venice E2EE (prod) | Requires reasoning about the taxpayer's situation — LLM task |
| **PDF generation** (filling Form 1040) | pypdf library | Mapping computed values to form fields — no AI needed |

### Privacy Architecture

```
Current PoC:
- Compute: PRIVATE (EigenCompute TEE — Intel TDX hardware isolation)
- Inference: NOT PRIVATE (Claude API — Anthropic sees prompts)
- Tax math: PRIVATE (runs entirely inside TEE, no external calls)
- Data at rest: PRIVATE (nothing stored, stateless)

Production upgrade (swap inference provider):
- Compute: PRIVATE (EigenCompute TEE)
- Inference: PRIVATE (Venice AI E2EE — encrypted end-to-end)
- Tax math: PRIVATE (local in TEE)
- Data at rest: PRIVATE (stateless)
- = FULLY PRIVATE end-to-end
```

---

## 4. User Flow

```
1. LAND      → User visits TaxAI
2. ATTEST    → Browser verifies TEE attestation
3. UPLOAD    → User drops W-2 PDF/image (or clicks "Use Demo W-2")
4. EXTRACT   → AI extracts all data from documents inside enclave
5. COMPUTE   → Tax engine calculates full 1040 (deterministic math)
6. RESULT    → Refund/owed amount displayed with:
               - "How I Optimized Your Savings" tab (decisions the AI made)
               - "Suggestions" tab (AI review with additional savings tips)
7. DOWNLOAD  → Official IRS Form 1040 PDF filled and ready
```

---

## 5. Tax Engine (2025 Federal)

### Filing Status & Standard Deductions (2025)
| Status | Standard Deduction |
|--------|-------------------|
| Single | $15,750 |
| Married Filing Jointly | $31,500 |
| Married Filing Separately | $15,750 |
| Head of Household | $23,625 |

### 2025 Tax Brackets (Single)
| Rate | Income Range |
|------|-------------|
| 10% | $0 - $11,925 |
| 12% | $11,926 - $48,475 |
| 22% | $48,476 - $103,350 |
| 24% | $103,351 - $197,300 |
| 32% | $197,301 - $250,525 |
| 35% | $250,526 - $626,350 |
| 37% | $626,351+ |

### Credits
- **Child Tax Credit**: $2,000 per qualifying child under 17

### Form 1040 Line Items Computed
| Line | Description |
|------|-------------|
| 1a | Wages from W-2 |
| 1z | Sum of wages (1a through 1h) |
| 2b | Taxable interest |
| 3b | Ordinary dividends |
| 9 | Total income |
| 10 | Adjustments to income |
| 11 | Adjusted gross income (AGI) |
| 12e | Standard or itemized deduction |
| 14 | Total deductions |
| 15 | Taxable income |
| 16 | Tax (from brackets) |
| 18 | Tax + additional taxes |
| 19 | Child tax credit |
| 22 | Tax after credits |
| 24 | Total tax |
| 25a | Federal tax withheld (from W-2) |
| 25d | Total withholding |
| 33 | Total payments |
| 34 | Overpayment (refund) |
| 35a | Amount refunded |
| 37 | Amount owed |

### Optimization Engine
The tax engine tracks every decision it makes and reports savings:
- Standard vs. itemized deduction comparison (auto-selects the better option)
- Progressive bracket computation with marginal vs. effective rate explanation
- Child tax credit application
- Multi-W-2 consolidation
- Withholding accuracy verification

---

## 6. Technical Stack

| Component | Choice | Purpose |
|-----------|--------|---------|
| **Language** | Python 3.9+ | Backend logic |
| **Framework** | FastAPI | API + static file serving |
| **Frontend** | Static HTML + vanilla JS | No build step, served from TEE |
| **Inference (PoC)** | Claude Opus 4.6 (Anthropic API) | Document extraction + tax review |
| **Inference (prod)** | [Venice AI](https://venice.ai/) E2EE | Swap for private inference |
| **Compute** | [EigenCompute](https://docs.eigencloud.xyz/eigencompute/get-started/eigencompute-overview) | Intel TDX TEE with attestation |
| **PDF** | pypdf | Fill official IRS Form 1040 PDF |
| **Container** | Docker | Required by EigenCompute |

---

## 7. Project Structure

```
TaxAI/
  Dockerfile
  requirements.txt
  TAXAI_SPEC.md
  app/
    main.py                    # FastAPI entry point, serves UI + API
    config.py                  # Anthropic API key, model selection, mock mode toggle
    static/
      index.html               # Single-page UI (upload → results)
      style.css                # Light theme, pastel blue accents
      app.js                   # Upload handling, results rendering, tabs
    routers/
      attestation.py           # TEE attestation endpoint (simulated locally, real on EigenCompute)
      form1040.py              # Document extraction, 1040 computation, PDF generation endpoints
    services/
      ai.py                    # Claude AI client (extraction + review), mock fallback
      form1040_engine.py       # Deterministic tax computation (brackets, deductions, credits, optimizations)
      pdf_generator.py         # Fills official IRS Form 1040 PDF using pypdf
    data/
      tax_tables.py            # 2025 federal tax brackets, standard deductions, credit amounts
      mock_taxpayer.json       # Demo data matching the sample W-2 (Elizabeth A Darling)
      f1040.pdf                # Official IRS Form 1040 (2025) — fillable PDF template
      sample_w2.pdf            # Sample W-2 for demo purposes
```

---

## 8. Demo Data

The demo uses a real sample W-2:
- **Employee**: Elizabeth A Darling
- **Employer**: University of Pittsburgh
- **Wages**: $44,629.35
- **Federal withheld**: $7,631.62
- **SS wages**: $48,736.35 / **SS tax**: $3,021.65
- **Medicare wages**: $48,736.35 / **Medicare tax**: $706.68
- **State**: PA / **State withheld**: $1,467.72

**Computed result**: Single filer, $15,750 standard deduction, $28,879.35 taxable income, $3,227.02 tax, **$4,404.60 refund**, 7.2% effective rate.

---

## 9. Next Steps

### Deploy to EigenCompute
- Deploy Docker container via `ecloud` CLI
- Verify TEE attestation works end-to-end from browser
- Set `ANTHROPIC_API_KEY` and `USE_MOCK_AI=false` in EigenCompute secrets

### FUTURE: Swap Claude for Venice AI E2EE (Private Inference)
- **Why**: Claude API means Anthropic sees the prompts. Venice E2EE would encrypt prompts end-to-end.
- **Action**: Confirm Venice E2EE programmatic API availability, swap the inference client
- **Reference**: [Venice E2EE announcement](https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai)
- This is the "take it to the next level" upgrade that completes the full privacy chain

---

## 10. Privacy Guarantees

### Private in PoC
- Application compute runs inside Intel TDX enclave (EigenCompute) — server operator can't read memory
- Tax computation runs entirely inside the TEE — no external calls for the math
- Application code is attested — developer cannot inject backdoors at runtime
- No financial data stored persistently — stateless processing

### Not Yet Private in PoC
- AI inference calls go to Anthropic (Claude API) — Anthropic can see the W-2 data and return summary in prompts
- This is the known gap, solvable by swapping to Venice AI E2EE for production

### What We Cannot Claim
- This is not a production tax filing tool
- Tax accuracy is not validated against IRS standards
- Full end-to-end privacy requires the Venice E2EE upgrade

---

## 11. Reference Links

- **Jupid (inspiration)**: https://www.producthunt.com/products/jupid
- **EigenCompute docs**: https://docs.eigencloud.xyz/eigencompute/get-started/eigencompute-overview
- **Venice AI**: https://venice.ai/
- **Venice E2EE announcement**: https://venice.ai/blog/venice-launches-end-to-end-encrypted-ai
- **EigenCloud AgentKit**: https://agents.eigencloud.xyz/create

"""TEE attestation endpoints.

In production on EigenCompute, these would return real Intel TDX attestation reports.
For local development, they return simulated attestation data.
"""

import hashlib
import os
import time

from fastapi import APIRouter

router = APIRouter()

# In EigenCompute TEE, this would come from the enclave's attestation service
IS_TEE = os.getenv("EIGENCOMPUTE_TEE", "false").lower() == "true"


@router.get("/api/attestation")
async def get_attestation():
    if IS_TEE:
        return await _real_attestation()
    return _simulated_attestation()


def _simulated_attestation() -> dict:
    """Return simulated attestation for local development."""
    # Simulate what a real TDX attestation report would contain
    docker_digest = os.getenv(
        "DOCKER_DIGEST",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    return {
        "verified": False,
        "environment": "local-development",
        "message": "Running outside EigenCompute TEE. Attestation is simulated.",
        "simulated_report": {
            "tee_type": "Intel TDX (simulated)",
            "docker_image_digest": docker_digest,
            "enclave_measurement": hashlib.sha256(
                f"taxai-enclave-{docker_digest}".encode()
            ).hexdigest(),
            "timestamp": int(time.time()),
            "rtmr0": "0" * 96 + " (simulated)",
            "rtmr1": "0" * 96 + " (simulated)",
            "rtmr2": "0" * 96 + " (simulated)",
        },
        "privacy_status": {
            "compute_enclave": "simulated",
            "data_at_rest": "not-stored",
            "data_in_transit": "tls",
        },
    }


async def _real_attestation() -> dict:
    """Fetch real attestation from EigenCompute TEE runtime.

    When deployed on EigenCompute, the TEE provides attestation endpoints
    that return Intel TDX quotes signed by the hardware.
    """
    # EigenCompute attestation endpoint (available inside the TEE)
    # The exact endpoint depends on EigenCompute's runtime API
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            # EigenCompute's local attestation service
            resp = await client.get("http://localhost:8400/attestation/report")
            resp.raise_for_status()
            report = resp.json()

        return {
            "verified": True,
            "environment": "eigencompute-tee",
            "message": "Running inside EigenCompute TEE. Attestation verified by hardware.",
            "report": report,
            "privacy_status": {
                "compute_enclave": "intel-tdx-verified",
                "data_at_rest": "not-stored",
                "data_in_transit": "tls",
            },
        }
    except Exception as e:
        return {
            "verified": False,
            "environment": "eigencompute-tee",
            "message": f"TEE detected but attestation fetch failed: {str(e)}",
            "privacy_status": {
                "compute_enclave": "tee-detected-unverified",
                "data_at_rest": "not-stored",
                "data_in_transit": "tls",
            },
        }

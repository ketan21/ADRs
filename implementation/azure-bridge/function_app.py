import azure.functions as func
import json
import logging
import os
import re
import uuid
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# ── Configuration ──
VAULT_URL = os.environ.get("KEY_VAULT_URL", "")
SECRET_PREFIX = "pega-test-op-"
ALLOWED_OPERATOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
MAX_OPERATOR_ID_LEN = 64

# ── Logger setup ──
logger = logging.getLogger(__name__)


def _sanitize_operator_id(raw: str) -> str:
    """Sanitize operator ID for use in AKV secret name."""
    # Strip anything that's not alphanumeric, underscore, hyphen
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "", raw)
    return sanitized[:MAX_OPERATOR_ID_LEN]


def _build_secret_name(operator_id: str) -> str:
    """AKV secret name: pega-test-op-<operatorId>"""
    return f"{SECRET_PREFIX}{operator_id}"


def main(req: func.HttpRequest) -> func.HttpResponse:
    correlation_id = req.headers.get("X-Correlation-Id", str(uuid.uuid4()))

    # Parse JSON body
    try:
        body = req.get_json()
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("[%s] Invalid JSON body: %s", correlation_id, e)
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    # Validate required fields
    operator_id = body.get("operatorId", "").strip()
    new_password = body.get("newPassword", "")
    timestamp = body.get("timestamp", "")
    environment = body.get("environment", "test").strip().lower()

    if not operator_id:
        logger.warning("[%s] Missing operatorId", correlation_id)
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: operatorId"}),
            status_code=400,
            mimetype="application/json",
        )

    if not new_password:
        logger.warning("[%s] Missing newPassword for operator=%s", correlation_id, operator_id)
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: newPassword"}),
            status_code=400,
            mimetype="application/json",
        )

    # Validate operator ID format
    if not ALLOWED_OPERATOR_ID_PATTERN.match(operator_id):
        logger.warning("[%s] Invalid operatorId format: %s", correlation_id, operator_id)
        return func.HttpResponse(
            json.dumps({"error": "Invalid operatorId format"}),
            status_code=400,
            mimetype="application/json",
        )

    # Sanitize for secret name
    safe_operator_id = _sanitize_operator_id(operator_id)
    secret_name = _build_secret_name(safe_operator_id)

    # Check vault URL configured
    if not VAULT_URL:
        logger.error("[%s] KEY_VAULT_URL environment variable not set", correlation_id)
        return func.HttpResponse(
            json.dumps({"error": "Server misconfiguration", "correlationId": correlation_id}),
            status_code=500,
            mimetype="application/json",
        )

    # ── Store secret in AKV ──
    try:
        # DefaultAzureCredential tries: env vars → managed identity → az cli → etc.
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=VAULT_URL, credential=credential)

        # Tags for audit and filtering
        tags = {
            "operator-id": safe_operator_id,
            "environment": environment,
            "last-rotated": timestamp or datetime.utcnow().isoformat() + "Z",
        }

        # Set the secret (creates new version)
        secret = client.set_secret(secret_name, new_password, tags=tags)

        logger.info(
            "[%s] Secret stored: name=%s version=%s operator=%s env=%s",
            correlation_id,
            secret_name,
            secret.properties.version,
            safe_operator_id,
            environment,
        )

        return func.HttpResponse(
            json.dumps({
                "status": "stored",
                "secretName": secret_name,
                "vaultUrl": VAULT_URL,
                "version": secret.properties.version,
                "tags": tags,
            }),
            status_code=201,
            mimetype="application/json",
        )

    except Exception as e:
        # Never log the password or full exception trace in production
        logger.error("[%s] Failed to store secret for operator=%s: %s", correlation_id, safe_operator_id, type(e).__name__)
        return func.HttpResponse(
            json.dumps({"error": "Failed to store secret", "correlationId": correlation_id}),
            status_code=500,
            mimetype="application/json",
        )

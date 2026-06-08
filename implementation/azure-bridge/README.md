# Azure Bridge — Pega Test Operator Password Rotation

Azure Function (Python, Consumption plan) that receives rotated passwords from Pega and stores them in Azure Key Vault.

## Architecture

```
Pega Job Scheduler
    ↓ Connect-REST POST JSON
Azure Function (HTTP Trigger)
    ↓ Managed Identity
Azure Key Vault (set_secret)
```

## API Contract

### POST /api/StoreTestOperatorPassword

**Headers:**
- `Content-Type: application/json`
- `X-Correlation-Id: <uuid>` (optional, for tracing)

**Body:**
```json
{
  "operatorId": "test_user_01",
  "newPassword": "...",
  "timestamp": "2025-06-08T14:30:00Z",
  "environment": "test"
}
```

**Response 201 Created:**
```json
{
  "status": "stored",
  "secretName": "pega-test-op-test_user_01",
  "vaultUrl": "https://<vault>.vault.azure.net/",
  "tags": {
    "operator-id": "test_user_01",
    "environment": "test",
    "last-rotated": "2025-06-08T14:30:00Z"
  }
}
```

**Response 400 Bad Request:**
```json
{"error": "Missing required field: operatorId"}
```

**Response 500 Internal Error:**
```json
{"error": "Failed to store secret", "correlationId": "..."}
```

## Security Rules

1. **Never log `newPassword`**. Log only `operatorId`, `timestamp`, `environment`.
2. **Managed Identity only**. No client secrets in config.
3. **Input validation**: `operatorId` must match `[A-Za-z0-9_-]+`. Max length 64.
4. **Secret naming**: `pega-test-op-<operatorId>`. Invalid characters are stripped.
5. **Soft-delete**: Vault must have soft-delete and purge protection enabled.

## Local Development

```bash
cd implementation/azure-bridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Authenticate with Azure CLI (dev fallback)
az login
func start
```

For local testing, the function uses `DefaultAzureCredential` which falls back to Azure CLI auth.

## Deployment

```bash
# Create Function App with system-assigned managed identity
az functionapp create \
  --resource-group my-rg \
  --name pega-password-bridge \
  --storage-account mystorage \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type linux

# Assign Key Vault Secrets Officer role to the Function's managed identity
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee-object-id <function-principal-id> \
  --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<vault>

# Deploy code
func azure functionapp publish pega-password-bridge
```

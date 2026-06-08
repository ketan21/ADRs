# Implementation Plan — Pega Test Operator Password Rotation + Azure Key Vault

## Overview
This plan details the step-by-step execution to deploy the automated password rotation system for Pega test operators, storing rotated passwords in Azure Key Vault.

## Prerequisites
- Pega Infinity 25 instance with administrative access
- Azure subscription with Owner/Contributor rights
- GitHub access to `ketan21/ADRs` repository
- Azure CLI installed locally for testing

---

## Phase 1: Azure Infrastructure (Days 1–2)

### 1.1 Create Azure Key Vault
```bash
az group create --name pega-password-rg --location westeurope

az keyvault create \
  --name pega-test-op-vault \
  --resource-group pega-password-rg \
  --location westeurope \
  --enable-soft-delete \
  --enable-purge-protection \
  --sku standard
```

### 1.2 Create Azure Function App
```bash
az storage account create \
  --name pegapwdstore \
  --resource-group pega-password-rg \
  --location westeurope \
  --sku Standard_LRS

az functionapp create \
  --resource-group pega-password-rg \
  --name pega-password-bridge \
  --storage-account pegapwdstore \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type linux
```

### 1.3 Configure Managed Identity
```bash
# Get Function's system-assigned principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --query principalId -o tsv)

# Grant Key Vault Secrets Officer
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee-object-id $PRINCIPAL_ID \
  --scope $(az keyvault show --name pega-test-op-vault --query id -o tsv)
```

### 1.4 Set Function Configuration
```bash
az functionapp config appsettings set \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --settings KEY_VAULT_URL="https://pega-test-op-vault.vault.azure.net/"
```

---

## Phase 2: Azure Bridge Deployment (Days 2–3)

### 2.1 Local Testing
```bash
cd implementation/azure-bridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Authenticate locally via Azure CLI
az login

# Start function locally
func start
```

### 2.2 Deploy to Azure
```bash
func azure functionapp publish pega-password-bridge
```

### 2.3 Verify Deployment
```bash
# Get function URL
az functionapp function show \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --function-name StoreTestOperatorPassword \
  --query invokeUrlTemplate -o tsv

# Test with curl
curl -X POST <function_url> \
  -H "Content-Type: application/json" \
  -d '{"operatorId":"test_user","newPassword":"TestPass123!","timestamp":"2025-06-08T00:00:00Z","environment":"test"}'
```

---

## Phase 3: Pega Configuration (Days 3–5)

### 3.1 Create Access Group
- **Access Group**: `TestAutomation:PasswordRotation`
- **Required access**: `Data-Admin-Operator-ID` (Full Access), `Rule-Connect-REST` (Full Access)
- **Work pool**: None (administrative task)

### 3.2 Create Data Pages
- **D_PegaTestOperator_RotatePassword.BridgeURL** — stores Azure Function endpoint URL
- **D_PegaEnv.Environment** — stores environment label (`test`, `dev`, `staging`)

### 3.3 Build Activity: `TestOperator_ExpiryCheckAndRotate`
See `implementation/pega/TestOperator_ExpiryCheckAndRotate.md` for full step-by-step specification.

Key implementation notes:
- Use `pxRandomString(16, "alphanumeric+symbols")` for password generation
- Set `.pyPassword` (not `.pyPasswordHash`) — Pega auto-hashes on `Obj-Save`
- Disable Connect-REST request/response logging for this connector
- Never write `Param.NewPassword` to audit entries

### 3.4 Create Connect-REST Rule
- **Rule name**: `TestOperator_RotatePassword`
- **Method**: POST
- **Endpoint**: read from `D_PegaTestOperator_RotatePassword.BridgeURL`
- **Headers**: `Content-Type: application/json`, `X-Correlation-Id`
- **Timeout**: 30 seconds
- **Retry**: 3 attempts with exponential backoff

### 3.5 Create Service Package (Optional)
If exposing rotation as on-demand service:
- **Service Package**: `TestOperator_RotatePassword`
- **Authentication**: Internal (for Job Scheduler) or OAuth 2.0 (for external callers)

---

## Phase 4: Job Scheduler Configuration (Day 5)

### 4.1 Create Job Scheduler Record
- **Record type**: Job Scheduler
- **Schedule**: Daily at 06:00 (or desired time)
- **Access group**: `TestAutomation:PasswordRotation`
- **Activity**: `TestOperator_ExpiryCheckAndRotate`
- **Node type**: Any (or specific background processing node)

### 4.2 Test Job Scheduler
1. Trigger manually via Admin Studio
2. Verify Activity runs without errors
3. Check AKV for newly stored secrets
4. Verify Pega operator records have updated `pyPasswordExpiryDate`

---

## Phase 5: Test Automation Integration (Day 6)

### 5.1 Local Development Setup
```bash
# Developers authenticate via Azure CLI
az login

# Set vault URL
export AZURE_KEY_VAULT_URL="https://pega-test-op-vault.vault.azure.net/"

# Run example
python implementation/test-automation/test_automation_example.py --operator test_user_01
```

### 5.2 Azure DevOps Pipeline Integration
```yaml
# azure-pipelines.yml snippet
steps:
- task: AzureCLI@2
  inputs:
    azureSubscription: 'MyAzureServiceConnection'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      export AZURE_KEY_VAULT_URL="https://pega-test-op-vault.vault.azure.net/"
      python -m pytest tests/
```

### 5.3 Grant Pipeline Access
Assign the Azure DevOps service principal `Get` permission on the Key Vault:
```bash
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id <pipeline-service-principal-id> \
  --scope $(az keyvault show --name pega-test-op-vault --query id -o tsv)
```

---

## Phase 6: Monitoring & Alerting (Day 7)

### 6.1 Application Insights
- Azure Function logs to Application Insights by default
- Create alert: HTTP 5xx rate > 1% over 5 minutes
- Create alert: Function execution time > 30 seconds

### 6.2 Pega Alerts
- Configure Pega alert for Job Scheduler failures
- Monitor `Data-Admin-Operator-ID` records with `pyPasswordExpiryDate` within 1 day
- Alert on Connect-REST timeout or 5xx responses

### 6.3 AKV Monitoring
- Enable Azure Monitor diagnostic logs on Key Vault
- Alert on unauthorized access attempts
- Review soft-delete recoveries periodically

---

## Rollback Plan

### Immediate Rollback (within 1 hour)
1. Disable Job Scheduler in Pega Admin Studio
2. Manually reset affected operator passwords via Pega Dev Studio
3. Update AKV secrets manually if needed

### Bridge Rollback
```bash
# Roll back to previous function deployment
az functionapp deployment source config-zip \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --src previous_version.zip
```

---

## Success Criteria
- [ ] Job Scheduler runs daily without errors
- [ ] All 10+ test operators have passwords rotated before expiry
- [ ] AKV secrets are updated within 1 minute of Pega rotation
- [ ] Test automation retrieves correct passwords from AKV
- [ ] No plaintext passwords in any logs
- [ ] All alerts are configured and tested

---

## Post-Implementation
- Review ADR-008 after 30 days — assess cold start impact
- Consider migrating to Premium plan if latency is critical
- Document any deviations from this plan in new ADRs
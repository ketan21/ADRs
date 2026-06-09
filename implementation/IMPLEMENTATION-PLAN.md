# Implementation Plan — Pega Test Operator Password Rotation + Azure Key Vault

## Overview
Day-by-day execution checklist. Each day has a **Goal**, the **commands/steps**, and a **What should exist at the end of this day** checkpoint.

## Prerequisites
- Azure subscription with Owner/Contributor rights
- Pega Infinity 25 administrative access
- GitHub access to `ketan21/ADRs`
- Azure CLI installed locally (`az --version`)

All resource naming:
- Resource group: `pega-password-rg`
- Key Vault: `pega-test-op-vault`
- Storage account: `pegapwdstore`
- Function App: `pega-password-bridge`

---

## Day 1 — Azure Resource Group + Key Vault

### What you do today
Create the Azure resource group and the Key Vault that will hold all rotated passwords.

### Commands
```bash
# Step 1.1 — Create resource group
az group create \
  --name pega-password-rg \
  --location westeurope

# Step 1.2 — Create Azure Key Vault
az keyvault create \
  --name pega-test-op-vault \
  --resource-group pega-password-rg \
  --location westeurope \
  --enable-soft-delete \
  --enable-purge-protection \
  --sku standard
```

### End-of-day checkpoint
- [ ] Resource group `pega-password-rg` exists in Azure portal
- [ ] Key Vault `pega-test-op-vault` exists with soft-delete and purge-protection enabled
- [ ] You can run `az keyvault show --name pega-test-op-vault` successfully

---

## Day 2 — Azure Function App + Managed Identity RBAC

### What you do today
Create the Storage Account required by the Function runtime, then create the Function App and grant its system-assigned Managed Identity permission to write to the Key Vault.

### Commands
```bash
# Step 2.1 — Create Storage Account (required for Function runtime internals)
az storage account create \
  --name pegapwdstore \
  --resource-group pega-password-rg \
  --location westeurope \
  --sku Standard_LRS

# Step 2.2 — Create Azure Function App
az functionapp create \
  --resource-group pega-password-rg \
  --name pega-password-bridge \
  --storage-account pegapwdstore \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type linux

# Step 2.3 — Enable system-assigned Managed Identity
# (az functionapp create already does this by default; verify it exists)
PRINCIPAL_ID=$(az functionapp identity show \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --query principalId -o tsv)

echo "Function Principal ID: $PRINCIPAL_ID"

# Step 2.4 — Grant Key Vault Secrets Officer
az role assignment create \
  --role "Key Vault Secrets Officer" \
  --assignee-object-id "$PRINCIPAL_ID" \
  --scope $(az keyvault show --name pega-test-op-vault --query id -o tsv)

# Step 2.5 — Set environment variable consumed by the bridge
az functionapp config appsettings set \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --settings KEY_VAULT_URL="https://pega-test-op-vault.vault.azure.net/"
```

### End-of-day checkpoint
- [ ] Storage Account `pegapwdstore` visible in Azure portal → Storage accounts
- [ ] Function App `pega-password-bridge` visible in Azure portal → Function App
- [ ] Identity tab on the Function App shows "System assigned: On" with an Object ID
- [ ] Key Vault → Access policies or RBAC shows the Function App principal with "Key Vault Secrets Officer"
- [ ] Application Settings on the Function App shows `KEY_VAULT_URL` defined

---

## Day 3 — Deploy Azure Bridge

### What you do today
Test the Azure Function locally, then deploy it.

### Commands
```bash
# Step 3.1 — Local testing
cd implementation/azure-bridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Authenticate locally (uses your Azure CLI login)
az login

# Start function locally
func start
```

In a new terminal (while `func start` is running):
```bash
# Step 3.2 — Local smoke test (assumes local endpoint http://localhost:7071)
curl -X POST http://localhost:7071/api/StoreTestOperatorPassword \
  -H "Content-Type: application/json" \
  -d '{"operatorId":"local_test","newPassword":"LocalTest123!","timestamp":"2025-06-08T00:00:00Z","environment":"test"}'
```

Expected response:
```json
{"status": "success", "message": "Secret stored successfully", "secretName": "test-operator-local-test"}
```

If local test passes, deploy:
```bash
# Step 3.3 — Deploy to Azure
func azure functionapp publish pega-password-bridge
```

Verify deployed function URL:
```bash
# Step 3.4 — Get production endpoint
az functionapp function show \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --function-name StoreTestOperatorPassword \
  --query invokeUrlTemplate -o tsv
```

### End-of-day checkpoint
- [ ] Local `func start` responds to curl with `status: success`
- [ ] Secret `test-operator-local-test` created in Azure Key Vault (verify in portal)
- [ ] `func azure functionapp publish` reported success
- [ ] Production function URL is visible and reachable
- [ ] You can POST to the production URL and receive `status: success`

---

## Day 4 — Pega Access Group + Data Pages + Connect-REST

### What you do today
Configure Pega with the Access Group, Data Pages, and Connect-REST rule needed by the rotation Activity.

### Steps

#### 4.1 Create Access Group
- **Rule name**: `TestAutomation:PasswordRotation`
- **Access roles** (add these to the Access Group):
  - `Data-Admin-Operator-ID` — Full Access (need to browse, open, save operator records)
  - `Rule-Connect-REST` — Full Access (need to create/update the Connect-REST rule)
- **Work pool**: None (this is an administrative task, not case-processing)

#### 4.2 Create Data Pages
| Data Page | Purpose | Sample Value |
|---|---|---|
| `D_PegaTestOperator_RotatePassword.BridgeURL` | Azure Function endpoint | `https://pega-password-bridge.azurewebsites.net/api/StoreTestOperatorPassword` |
| `D_PegaEnv.Environment` | Environment label for AKV secret naming | `test` |

#### 4.3 Create Connect-REST Rule
- **Rule name**: `TestOperator_RotatePassword`
- **Method**: POST
- **Endpoint**: read from `D_PegaTestOperator_RotatePassword.BridgeURL` at runtime
- **Headers**: `Content-Type: application/json`, `X-Correlation-Id` (generate UUID)
- **Timeout**: 30 seconds
- **Retry**: 3 attempts with exponential backoff (2s, 4s, 8s)

**Security setting**: Disable request/response logging on this connector so the plaintext password is never written to Pega logs.

### End-of-day checkpoint
- [ ] Access Group `TestAutomation:PasswordRotation` exists in Pega Dev Studio
- [ ] Data page `D_PegaTestOperator_RotatePassword.BridgeURL` resolves to the Azure Function URL
- [ ] Connect-REST rule `TestOperator_RotatePassword` is configured and can be traced/tested
- [ ] Running the Connect-REST test from Pega Dev Studio results in HTTP 200 with `status: success`

---

## Day 5 — Pega Activity + Job Scheduler

### What you do today
Build the `TestOperator_ExpiryCheckAndRotate` Activity that ties everything together, then create the Job Scheduler to run it on a schedule.

### Steps

#### 5.1 Build Activity: `TestOperator_ExpiryCheckAndRotate`
See `implementation/pega/TestOperator_ExpiryCheckAndRotate.md` for the complete step-by-step specification.

Key implementation reminders:
- Browse `Data-Admin-Operator-ID` where <use your org's mechanism: e.g. `pyLastPasswordChangedTime`, `pxPasswordHistory`, or Security Policy-driven expiry>
- Generate password: `pxRandomString(16, "alphanumeric+symbols")`
- Set `.pyPassword` (not `.pyPasswordHash`) — Pega auto-hashes on `Obj-Save`
- Call Connect-REST `TestOperator_RotatePassword` with the new password
- Save operator record

**Never write `Param.NewPassword` into audit entries or Clipboard trace data.**

#### 5.2 Create Job Scheduler Record
- **Record type**: Job Scheduler
- **Schedule**: Daily at 06:00 (or your preferred time)
- **Access group**: `TestAutomation:PasswordRotation`
- **Activity**: `TestOperator_ExpiryCheckAndRotate`
- **Node type**: Any (or assign to a specific background processing node)

#### 5.3 Manual Test
1. Identify a test operator whose password has not been rotated recently (check `pyLastPasswordChangedTime` or `pxPasswordHistory`)
2. Trigger the Job Scheduler manually from Admin Studio
3. Watch the Activity trace
4. Verify in Azure Key Vault that a new secret was created (or version updated)
5. Verify the operator's `pyLastPasswordChangedTime` is updated (Pega updates this automatically on `Obj-Save` of `.pyPassword`)

### End-of-day checkpoint
- [ ] Activity `TestOperator_ExpiryCheckAndRotate` created and checked in
- [ ] Job Scheduler created and active in Admin Studio
- [ ] Manual trigger rotated at least one test operator password
- [ ] Azure Key Vault shows new secret version for that operator
- [ ] Operator record updated (Pega updates `pyLastPasswordChangedTime` automatically on `Obj-Save` of `.pyPassword`)

---

## Day 6 — Test Automation Integration

### What you do today
Configure local test automation and Azure DevOps pipelines to consume rotated passwords from Azure Key Vault.

### Steps

#### 6.1 Local Development Setup
```bash
# Authenticate via Azure CLI
az login

# Set vault URL for your session
export AZURE_KEY_VAULT_URL="https://pega-test-op-vault.vault.azure.net/"

# Run the example
python implementation/test-automation/test_automation_example.py --operator test_user_01
```

#### 6.2 Azure DevOps Pipeline Integration
```yaml
# azure-pipelines.yml snippet
steps:
- checkout: self
- task: AzureCLI@2
  inputs:
    azureSubscription: 'MyAzureServiceConnection'
    scriptType: 'bash'
    scriptLocation: 'inlineScript'
    inlineScript: |
      export AZURE_KEY_VAULT_URL="https://pega-test-op-vault.vault.azure.net/"
      python -m pytest tests/
```

#### 6.3 Grant Pipeline Access
```bash
# Get the Azure DevOps service principal object ID from your pipeline service connection
# Then grant it read-only access
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id <pipeline-service-principal-id> \
  --scope $(az keyvault show --name pega-test-op-vault --query id -o tsv)
```

### End-of-day checkpoint
- [ ] Local script runs and prints the latest rotated password for a test operator (do not log the actual value)
- [ ] Azure DevOps pipeline job can access Azure Key Vault without errors
- [ ] Pipeline runs `pytest` and passes using the rotated credentials

---

## Day 7 — Monitoring, Alerts + Final Verification

### What you do today
Configure monitoring for all three components (Azure Function, Pega, AKV) and run the end-to-end success checklist.

### Steps

#### 7.1 Azure Function Monitoring
Azure Functions log to Application Insights automatically. Configure alerts:
- HTTP 5xx rate > 1% over 5 minutes
- Function execution time > 30 seconds
- Function execution failure count > 0 in 5 minutes

#### 7.2 Pega Alerts
- Configure Pega alert for Job Scheduler failures
- Monitor `Data-Admin-Operator-ID` records that have not been rotated per your Security Policy schedule
- Alert on Connect-REST timeout or 5xx responses

#### 7.3 Key Vault Monitoring
- Enable Azure Monitor diagnostic logs on Key Vault
- Alert on unauthorized access attempts
- Review soft-delete recoveries periodically

#### 7.4 Final Verification Checklist
- [ ] Job Scheduler runs daily without errors
- [ ] All 10+ test operators have passwords rotated (verify via `pyLastPasswordChangedTime` or `pxPasswordHistory`)
- [ ] AKV secrets are updated within 1 minute of Pega rotation
- [ ] Test automation retrieves correct passwords from AKV
- [ ] No plaintext passwords in any logs
- [ ] All alerts are configured and tested

---

## Quick Reference: All Azure Resources Created

| Resource | Name | Purpose |
|---|---|---|
| Resource Group | `pega-password-rg` | Holds all Azure resources |
| Key Vault | `pega-test-op-vault` | Stores rotated passwords |
| Storage Account | `pegapwdstore` | Required by Azure Function runtime internals |
| Function App | `pega-password-bridge` | HTTP bridge between Pega and AKV |

---

## Rollback Plan

### Immediate Rollback (within 1 hour of discovery)
1. Disable Job Scheduler in Pega Admin Studio
2. Manually reset affected operator passwords via Pega Dev Studio
3. If needed, delete the AKV secret version created during the bad run

### Bridge Rollback
```bash
# Roll back to previous function deployment (if you kept the deployment zip)
az functionapp deployment source config-zip \
  --name pega-password-bridge \
  --resource-group pega-password-rg \
  --src previous_version.zip
```

---

## Post-Implementation
- Review ADR-008 after 30 days — assess cold start impact
- Consider migrating to Premium plan if latency is critical
- Document any deviations from this plan in new ADRs
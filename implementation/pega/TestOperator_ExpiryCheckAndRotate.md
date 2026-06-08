# Pega Activity — TestOperator_ExpiryCheckAndRotate

## Purpose
Job Scheduler Activity that:
1. Finds test operators whose passwords expire within 3 days
2. Generates a new password
3. Updates the operator record (`Data-Admin-Operator-ID`)
4. Sends the new password to the Azure bridge via `Connect-REST`

## Trigger
Pega Job Scheduler, daily at 06:00, running under `TestAutomation:NoExpiry` access group (or dedicated admin access group with `Data-Admin-Operator-ID` full access).

## Activity Steps

### Step 1: Initialize
```
Property-Set
  .pxRequestor.pyAccessGroup = "TestAutomation:NoExpiry"
```

### Step 2: Find expiring operators (Obj-Browse)
```
Obj-Browse
  Class: Data-Admin-Operator-ID
  Filter: pyAccessGroup IN ("TestAutomation:Operators", "TestAutomation:NoExpiry")
  Filter: pyPasswordExpiryDate <= @(addDays(@CurrentDateTime(), 3))
  Results: .pxResults
```

### Step 3: Loop over each operator
```
For Each .pxResults
```

### Step 3a: Generate new password
```
Property-Set
  Param.NewPassword = @pxRandomString(16, "alphanumeric+symbols")
```

### Step 3b: Update operator record
```
Property-Set
  .pyPassword = Param.NewPassword
  .pyPasswordExpiryDate = @addDays(@CurrentDateTime(), 30)

Obj-Save
  Class: Data-Admin-Operator-ID
  WriteNow: true
```

### Step 3c: Call Azure bridge (Connect-REST)
```
Property-Set
  Param.BridgeUrl = @D_PegaTestOperator_RotatePassword.BridgeURL
  Param.JsonBody = {
    "operatorId": .pyUserIdentifier,
    "newPassword": Param.NewPassword,
    "timestamp": @CurrentDateTime(),
    "environment": @D_PegaEnv.Environment
  }

Connect-REST
  Method: POST
  URL: Param.BridgeUrl
  Headers:
    Content-Type: application/json
    X-Correlation-Id: @pxGenerateUniqueID()
  Body: Param.JsonBody
  Timeout: 30 seconds
  On Error: jump to Step 3d (mark failed, continue loop)
```

### Step 3d: Audit log (on success or failure)
```
Activity: WriteAuditEntry
  Param.OperatorId = .pyUserIdentifier
  Param.Status = "SUCCESS" or "FAILED"
  Param.CorrelationId = @pxRequestor.pyCorrelationId
  Param.ErrorMessage = .pxErrorMessage (if failed)
```

**Note**: `Param.NewPassword` is never written to the audit entry. Only `operatorId`, `status`, `correlationId` are logged.

## Error Handling
- If `Obj-Save` fails: skip this operator, log error, continue loop
- If `Connect-REST` fails (timeout, 5xx, 4xx): mark operator as "needs manual rotation", log correlation ID, continue loop
- If bridge returns 201 but `Obj-Save` had already succeeded: operator has new password in Pega and AKV. Safe state.
- If bridge returns 201 but `Obj-Save` failed: **inconsistent state** — Pega has old password, AKV has new. Alert admin.

## Connect-REST Service Package
- **Service Package**: `TestOperator_RotatePassword`
- **Authentication**: Internal (no external callers; Job Scheduler uses requestor pool)
- **Requestor Pool**: Dedicated access group with `Data-Admin-Operator-ID` full access
- **Timeout**: 30 seconds
- **Retry**: 3 attempts with exponential backoff (handled by Pega Connect-REST rule)

## Security Notes
- The plaintext password exists only in `Param.NewPassword` and the JSON body of the REST call.
- Pega tracer, logs, and `pxRequestor` must **not** capture Connect-REST body contents. Disable request/response logging for this connector.
- Use `pxChangePassword` or `setPassword` utilities if available in your Pega version, but the mechanism above (`pyPassword` + `Obj-Save`) is the standard programmatic approach.

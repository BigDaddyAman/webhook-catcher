# Simple Testing Guide - Webhook Catcher

Quick commands to test the webhook catcher deployment.

**Replace `YOUR-DEPLOYMENT-URL` with your actual deployment URL**

## 🧪 Basic Tests

### Health Check
```bash
# Unix/Linux/macOS
curl https://YOUR-DEPLOYMENT-URL.up.railway.app/healthz

# Windows CMD
curl https://YOUR-DEPLOYMENT-URL.up.railway.app/healthz

# Windows PowerShell
Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/healthz"
```

### List Available Webhooks (for replay testing)
```bash
# Unix/Linux/macOS
curl https://YOUR-DEPLOYMENT-URL.up.railway.app/webhooks

# Windows CMD
curl https://YOUR-DEPLOYMENT-URL.up.railway.app/webhooks

# Windows PowerShell
Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhooks"
```

### Simple Webhook Test
```bash
# Unix/Linux/macOS
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "message": "Hello World!"}'

# Windows CMD
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" ^
  -H "Content-Type: application/json" ^
  -d "{\"event\": \"test\", \"message\": \"Hello World!\"}"
```

```powershell
# Windows PowerShell
$body = @{
    event = "test"
    message = "Hello World!"
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" `
  -Method POST -Body $body -ContentType "application/json"
```

### Complex JSON Test
```bash
# Unix/Linux/macOS
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" \
  -H "Content-Type: application/json" \
  -d '{"user": {"id": 123, "name": "Hello"}, "event": "signup"}'

# Windows CMD
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" ^
  -H "Content-Type: application/json" ^
  -d "{\"user\": {\"id\": 123, \"name\": \"Hello\"}, \"event\": \"signup\"}"
```

```powershell
# Windows PowerShell
$body = @{
    user = @{
        id = 123
        name = "testuser"
        email = "test@example.com"
    }
    event = "signup"
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" `
  -Method POST -Body $body -ContentType "application/json"
```

### GitHub-style Test
```bash
# Unix/Linux/macOS
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"action": "opened", "repository": {"name": "test-repo"}}'

# Windows CMD
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" ^
  -H "Content-Type: application/json" ^
  -H "X-GitHub-Event: push" ^
  -d "{\"action\": \"opened\", \"repository\": {\"name\": \"test-repo\"}}"
```

```powershell
# Windows PowerShell
$body = @{
    action = "opened"
    repository = @{
        name = "test-repo"
        full_name = "user/test-repo"
    }
    pull_request = @{
        title = "Test Pull Request"
        user = @{ login = "testuser" }
    }
} | ConvertTo-Json -Depth 3

$headers = @{
    "Content-Type" = "application/json"
    "X-GitHub-Event" = "push"
}

Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" `
  -Method POST -Body $body -Headers $headers
```

## 🔒 Admin Protection Tests

### Check Admin Status
```bash
# Unix/Linux/macOS
curl https://YOUR-DEPLOYMENT-URL.up.railway.app/healthz

# Windows CMD
curl https://YOUR-DEPLOYMENT-URL.up.railway.app/healthz

# Windows PowerShell
Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/healthz"
```
**Look for**: `"admin_protected": true/false`

### Test Clear Without Token (Should Fail if Protected)
```bash
# Unix/Linux/macOS
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/clear"

# Windows CMD
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/clear"

# Windows PowerShell
Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/clear" -Method POST
```
**Expected if protected**: `401 Unauthorized`

### Test Clear With Admin Token (Should Work)
```bash
# Unix/Linux/macOS
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/clear" \
  -H "X-Admin-Token: your-secret-admin-token-123"

# Windows CMD
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/clear" ^
  -H "X-Admin-Token: your-secret-admin-token-123"
```

```powershell
# Windows PowerShell
$headers = @{"X-Admin-Token" = "your-secret-admin-token-123"}
Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/clear" `
  -Method POST -Headers $headers
```
**Expected**: `{"status": "cleared"}`

### Test Replay With Admin Token

**Step 1: Send a webhook to replay**
```powershell
# Windows PowerShell
$testBody = @{
    test = "replay"
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    message = "This will be replayed"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhook" `
  -Method POST -Body $testBody -ContentType "application/json"
```

**Step 2: List webhooks to get the ID**
```powershell
# Windows PowerShell
$webhooks = Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/webhooks"
Write-Host "Available webhooks:"
$webhooks.webhooks | Format-Table id, timestamp, body_preview
```

**Step 3: Replay the webhook (use the correct ID from step 2)**
```bash
# Unix/Linux/macOS - Replace {ID} with actual webhook ID
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/replay/{ID}?target_url=https://httpbin.org/post" \
  -H "X-Admin-Token: your-secret-admin-token-123"

# Windows CMD - Replace {ID} with actual webhook ID
curl -X POST "https://YOUR-DEPLOYMENT-URL.up.railway.app/replay/{ID}?target_url=https://httpbin.org/post" ^
  -H "X-Admin-Token: your-secret-admin-token-123"
```

```powershell
# Windows PowerShell - Replace {ID} with actual webhook ID from step 2
$webhookId = 1  # Use the actual ID from the list above
$headers = @{"X-Admin-Token" = "your-secret-admin-token-123"}
Invoke-RestMethod -Uri "https://YOUR-DEPLOYMENT-URL.up.railway.app/replay/$webhookId?target_url=https://httpbin.org/post" `
  -Method POST -Headers $headers
```

## 🧪 Complete Test Workflow Scripts

### PowerShell Complete Test
Save as `complete-test.ps1`:
```powershell
param(
    [string]$BaseUrl = "https://YOUR-DEPLOYMENT-URL.up.railway.app",
    [string]$AdminToken = "your-secret-admin-token-123"
)

Write-Host "🚀 Testing Webhook Catcher: $BaseUrl" -ForegroundColor Green

# 1. Health Check
Write-Host "`n1. Health Check" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/healthz"
    Write-Host "✅ Status: $($health.status)" -ForegroundColor Green
    Write-Host "✅ Admin Protected: $($health.admin_protected)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Send Test Webhook
Write-Host "`n2. Sending Test Webhook" -ForegroundColor Yellow
$testBody = @{
    event = "complete-test"
    message = "PowerShell test webhook"
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    source = "PowerShell Script"
} | ConvertTo-Json

try {
    $webhookResult = Invoke-RestMethod -Uri "$BaseUrl/webhook" `
        -Method POST -Body $testBody -ContentType "application/json"
    Write-Host "✅ Webhook sent: $($webhookResult.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Webhook send failed: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. List Available Webhooks
Write-Host "`n3. Listing Available Webhooks" -ForegroundColor Yellow
try {
    $webhooks = Invoke-RestMethod -Uri "$BaseUrl/webhooks"
    Write-Host "✅ Found $($webhooks.count) webhooks" -ForegroundColor Green
    
    if ($webhooks.count -gt 0) {
        $latestId = $webhooks.webhooks[0].id
        Write-Host "📋 Latest webhook ID: $latestId" -ForegroundColor Cyan
        
        # 4. Test Replay
        Write-Host "`n4. Testing Webhook Replay" -ForegroundColor Yellow
        $headers = @{"X-Admin-Token" = $AdminToken}
        try {
            $replayResult = Invoke-RestMethod -Uri "$BaseUrl/replay/$latestId?target_url=https://httpbin.org/post" `
                -Method POST -Headers $headers
            Write-Host "✅ Replay successful: $($replayResult.status)" -ForegroundColor Green
            Write-Host "📊 Response status: $($replayResult.response_status)" -ForegroundColor Cyan
        } catch {
            Write-Host "❌ Replay failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "❌ Webhook listing failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎉 Test complete! Check your webhook UI at: $BaseUrl" -ForegroundColor Magenta
Write-Host "📋 View logs at: $BaseUrl/logs/view" -ForegroundColor Magenta
```

### Unix/Linux/macOS Test Script
Save as `complete-test.sh`:
```bash
#!/bin/bash
BASE_URL="${1:-https://YOUR-DEPLOYMENT-URL.up.railway.app}"
ADMIN_TOKEN="${2:-your-secret-admin-token-123}"

echo "🚀 Testing Webhook Catcher: $BASE_URL"

# 1. Health Check
echo "1. Health Check"
HEALTH=$(curl -s "$BASE_URL/healthz")
echo "✅ Health: $HEALTH"

# 2. Send Test Webhook
echo "2. Sending Test Webhook"
WEBHOOK_RESULT=$(curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -d "{\"event\": \"bash-test\", \"message\": \"Hello from bash!\", \"timestamp\": \"$(date -Iseconds)\"}")
echo "✅ Webhook: $WEBHOOK_RESULT"

# 3. List Webhooks
echo "3. Listing Webhooks"
WEBHOOKS=$(curl -s "$BASE_URL/webhooks")
echo "✅ Webhooks: $WEBHOOKS"

# 4. Get latest webhook ID and replay
LATEST_ID=$(echo "$WEBHOOKS" | jq -r '.webhooks[0].id // empty')
if [ ! -z "$LATEST_ID" ]; then
    echo "4. Replaying webhook ID: $LATEST_ID"
    REPLAY_RESULT=$(curl -s -X POST "$BASE_URL/replay/$LATEST_ID?target_url=https://httpbin.org/post" \
      -H "X-Admin-Token: $ADMIN_TOKEN")
    echo "✅ Replay: $REPLAY_RESULT"
fi

echo "🎉 Test complete! Check your webhook UI at: $BASE_URL"
```

## 🌐 Web Interface Testing

1. Visit: `https://YOUR-DEPLOYMENT-URL.up.railway.app/`
2. Check logs: `https://YOUR-DEPLOYMENT-URL.up.railway.app/logs/view`
3. Send test webhook using the built-in form
4. Try search, export, and replay features
5. Test admin operations (clear, replay) with/without protection

## ✅ Expected Results

- All webhook tests return `{"status": "success", ...}`
- Webhooks appear in real-time on the web interface
- `/webhooks` endpoint lists available webhook IDs
- Search and export functions work
- Health check returns `{"status": "ok", "admin_protected": true/false}`
- Admin operations respect token protection if enabled
- Replay works with correct webhook IDs from `/webhooks` endpoint

## 🚨 Common Issues & Solutions

### Issue: "Webhook not found" during replay
**Solution**: Use `GET /webhooks` to see available webhook IDs first

### Issue: "Internal Server Error" during replay
**Solution**: Check that the target URL is valid (starts with http:// or https://)

### Issue: Admin token not working
**Solution**: Ensure ADMIN_TOKEN environment variable is set correctly

### Issue: No webhooks showing up
**Solution**: Send a test webhook first using the `/webhook` endpoint

## 🏆 Key Features to Evaluate

- **Multi-service architecture** (if FORWARD_WEBHOOK_URL is configured)
- **Real-time web interface** with live updates
- **Multiple webhook formats** (JSON, plain text, form data)
- **Production features** (search, export, replay, admin protection)
- **Security features** (admin token protection for sensitive operations)
- **Cross-platform compatibility** (Unix, Windows CMD, PowerShell)
- **Error handling** (proper HTTP status codes and error messages)

Total testing time: ~5 minutes

---

## 📝 Quick Setup 

⚡ This project is optimized for Railway, but you can deploy it anywhere you like.

1. Deploy using your preferred platform (Railway recommended for easiest setup)
2. Copy your deployment URL from your hosting dashboard
3. Replace `YOUR-DEPLOYMENT-URL` in commands above
4. Run tests to evaluate the webhook catcher
5. Test on your preferred platform (Unix/Windows/PowerShell)
6. Use `/webhooks` endpoint to get valid IDs before replay testing

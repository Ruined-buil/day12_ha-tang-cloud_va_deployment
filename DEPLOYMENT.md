# Deployment Information

## Public URL
https://day12-lab-complete-production-1b0f.up.railway.app/

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://day12-lab-complete-production-1b0f.up.railway.app/health
# Expected: {"status": "ok", ...}
```
LOG RUN
$ curl https://day12-lab-complete-production-1b0f.up.railway.app/health
{"status":"ok","uptime_seconds":604.1,"total_requests":8,"timestamp":"2026-04-17T15:30:04.121854+00:00"}

### Readiness Check
```bash
curl https://day12-lab-complete-production-1b0f.up.railway.app/ready
# Expected: {"ready": true}
```
LOGRUN 
$ curl https://day12-lab-complete-production-1b0f.up.railway.app/ready
{"ready":true}

### API Test (without authentication)
```bash
curl -X POST https://day12-lab-complete-production-1b0f.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Expected: 401 Unauthorized
```

### API Test (with authentication)
```bash
# Note: Replace YOUR_KEY with real AGENT_API_KEY
curl -X POST https://day12-lab-complete-production-1b0f.up.railway.app/ask \
  -H "X-API-Key: my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```

## Environment Variables Set
- `PORT`: 8000
- `REDIS_URL`: redis://... (managed by Railway)
- `AGENT_API_KEY`: [Configured in Railway]
- `LOG_LEVEL`: INFO
- `ENVIRONMENT`: production


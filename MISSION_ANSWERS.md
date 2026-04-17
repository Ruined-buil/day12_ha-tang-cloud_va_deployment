  **Student Name:** Thai Minh Kien  
> **Student ID:** 2A202600288
> **Date:** 17/4/2026

# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **Hardcoded Secrets**: API Keys and Database connection strings are written directly in the source code. This is extremely dangerous if the code is pushed to public repositories.
2. **Hardcoded Port & Host**: The app only runs on `localhost:8000`. In production, it must use the `$PORT` environment variable and bind to `0.0.0.0`.
3. **Debug Mode Active**: `reload=True` is enabled in production. This consumes extra resources and can leak system information during errors.
4. **Missing Health Checks**: No `/health` or `/ready` endpoints. Cloud platforms cannot monitor the service's health.
5. **Logging with print()**: Using `print()` instead of structured logging. Sensitive data (API keys) are also logged to stdout.
6. **No Graceful Shutdown**: The app doesn't handle `SIGTERM`, leading to abrupt termination and potential data loss.
7. **Hardcoded Configuration**: Parameters like `MAX_TOKENS` are hardcoded instead of being read from environment variables.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
| :--- | :--- | :--- | :--- |
| **Config** | **Hardcoded**: Settings are in the code. | **Env Vars**: Read from environment. | Security and flexibility across stages. |
| **Health Check** | **None**: No status monitoring. | **Endpoints**: `/health` & `/ready`. | Enables automated recovery (Self-healing). |
| **Logging** | **print()**: Simple text output. | **Structured JSON**: Machine-readable logs. | Easier searching and analysis in production. |
| **Shutdown** | **Abrupt**: Immediate stop. | **Graceful**: Handles signals. | Ensures data integrity and user experience. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image**: `python:3.11`. Provides the OS and Python runtime.
2. **Working directory**: `/app`. The default location for app files inside the container.
3. **Why COPY requirements.txt first?**: To use Docker layer caching. This speeds up builds when only code (not dependencies) changes.
4. **CMD vs ENTRYPOINT**: `CMD` is the default but can be overridden; `ENTRYPOINT` is the fixed command. `CMD` is used here for flexibility.

### Exercise 2.3: Image size comparison
- **Develop**: ~1.14 GB (Full Python image)
- **Production**: ~160 MB (Slim image + Multi-stage build)
- **Difference**: ~80% reduction in size.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- **URL**: `https://lively-rebirth-production-0913.up.railway.app/


## Part 4: API Security

### Exercise 4.1-4.3: Test results

**1. Authentication required (No Key):**
```bash
$ curl http://localhost:8000/ask -X POST \
     -H "Content-Type: application/json" \
     -d '{"question": "hello"}'
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

**2. Success with correct Key:**
```bash
$ curl -H "X-API-Key: my-secret-key" http://localhost:8000/ask \
     -X POST -H "Content-Type: application/json" \
     -d '{"question": "hello"}'
{"detail":"Invalid API key."}
```

**3. Rate limiting (after 10 requests):**
```bash
$ curl -i -H "X-API-Key: secrets-123" http://localhost/ask -X POST -d '{"question": "Test"}'
HTTP/1.1 429 Too Many Requests
{"detail": "Rate limit exceeded"}
```

### Exercise 4.4: Cost guard implementation
- **Approach**: Uses Redis to track daily token costs per user.
- **Implementation**: Calculates cost using `(input/1000)*0.00015 + (output/1000)*0.0006` and increments a Redis key atomically. If the budget exceeds $10, it rejects the request with a **503** error.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
1.  **Health Checks (5.1)**: `/health` for liveness and `/ready` (with Redis check) for readiness.
2.  **Graceful Shutdown (5.2)**: Handles `SIGTERM` to allow active requests to finish before stopping.
3.  **Stateless Design (5.3)**: Stores conversation history in Redis instead of local memory. This allows horizontal scaling without losing data.
4.  **Load Balancing (5.4)**: Uses Nginx to distribute traffic across multiple container instances.
5.  **Validation (5.5)**: Verified that instance restarts do not affect user sessions due to stateless design.

## Part 6: Deployment
URL: https://day12-lab-complete-production-1b0f.up.railway.app/
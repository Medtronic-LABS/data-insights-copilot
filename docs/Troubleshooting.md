# Troubleshooting & Debugging

This page helps diagnose and fix common issues in the Data Insights Copilot.

## Common Issues

### 1. Database Connection Errors

- **Error**: `OperationalError: could not connect to server`
- **Cause**: PostgreSQL is not running or incorrect credentials.
- **Fix**:
    1.  Check if Postgres is running:
        ```bash
        docker ps | grep postgres
        ```
    2.  Verify credentials in `.env` match `docker-compose.yml`.

### 2. OpenAI API Errors

- **Error**: `RateLimitError` or `AuthenticationError`
- **Cause**: Invalid API key or quota exceeded.
- **Fix**:
    - Verify `OPENAI_API_KEY` is set correctly.
    - Check usage limits on OpenAI dashboard.

### 3. Frontend Build Failure

- **Error**: `Vite build failed`
- **Fix**:
    - Clear node_modules: `rm -rf node_modules && npm install`.
    - Check TypeScript errors: `npm run type-check`.

### 4. "No relevant documents found" (RAG)

- **Cause**: Vector store is empty or embeddings are corrupted.
- **Fix**:
    - Re-run ingestion via the configuration page.
    - Check logs for embedding failures.

### 5. "No active LLM provider configured"

- **Error**: `RuntimeError: No active LLM provider configured`
- **Cause**: LLM registry failed to initialize on startup.
- **Fix**:
    1. Check your LLM provider API key is set:
       ```bash
       echo $OPENAI_API_KEY  # Should not be empty
       ```
    2. Check database for valid LLM settings:
       ```bash
       sqlite3 backend/sqliteDb/app.db "SELECT * FROM system_settings WHERE category='llm';"
       ```
    3. Review backend logs for specific initialization errors.
    4. Try resetting LLM config via API:
       ```bash
       curl -X PUT http://localhost:8000/api/v1/settings/llm \
         -H "Authorization: Bearer $TOKEN" \
         -H "Content-Type: application/json" \
         -d '{"provider": "openai", "config": {"api_key": "your-key"}}'
       ```

### 6. Langfuse Tracing Not Working

- **Error**: No traces appearing in Langfuse dashboard
- **Cause**: Incorrect credentials or connection issues.
- **Fix**:
    1. Verify environment variables:
       ```bash
       echo $LANGFUSE_PUBLIC_KEY
       echo $LANGFUSE_SECRET_KEY
       echo $LANGFUSE_HOST
       ```
    2. Check Langfuse is running (if self-hosted):
       ```bash
       curl http://localhost:3001/api/public/health
       ```
    3. Look for initialization message in logs:
       ```
       ✅ Langfuse tracing enabled
       ```
    4. If using local Langfuse, ensure Docker containers are running:
       ```bash
       docker-compose -f docker-compose.langfuse.yml ps
       ```

### 8. `ERR_EMPTY_RESPONSE` or SQL Query Timeouts

- **Error**: API returns `ERR_EMPTY_RESPONSE` or a 504 Gateway Timeout during dashboard generation.
- **Cause**: High-concurrency dashboard synthesis blocking the event loop or exceeding the 60s timeout.
- **Fix**:
    1.  Verify the `SQLService` **Async-to-Sync Bridge** is enabled.
    2.  Check the database connection pool settings (increase `POSTGRES_MAX_OVERFLOW` if needed).
    3.  See [Concurrency Guide](../docs/CONCURRENCY_GUIDE.md) for tuning parameters.

### 9. Redis/Celery Task Stalling

- **Error**: Embedding jobs stay in `QUEUED` or `PREPARING` indefinitely.
- **Cause**: Redis backend is full or the Celery worker is not responding.
- **Fix**:
    1.  Check Redis health: `docker exec data_insights_redis redis-cli ping`.
    2.  Verify Celery Beat is running: `conda run -n data-insights-copilot celery -A backend.app.core.celery_app inspect ping`.
    3.  Clear the task queue if it's deadlocked: `redis-cli flushall`.

### 10. Qdrant Dimension Mismatch

- **Error**: `GRPC Error: Invalid vector dimension: expected 1536, got 1024`.
- **Cause**: The agent's selected embedding model changed, but the existing Qdrant collection uses a different dimension.
- **Fix**:
    1.  Navigate to the Agent settings.
    2.  Click **Force Re-index**. This will purge the old collection and recreate it with the correct dimensions for the new model.

### 11. HuggingFace Model Download Failures

- **Error**: `OSError: [Errno 28] No space left on device` or `ReadTimeout`.
- **Cause**: Insufficient disk space for weights or stable internet connection.
- **Fix**:
    1.  Ensure `/backend/data/models` has at least 10GB of free space.
    2.  Increase `HF_HUB_TIMEOUT` in `.env` if your connection is slow.

## Debugging

### Checking Logs

- **Backend**:
    ```bash
    docker logs fhir_rag_backend
    # or local
    tail -f backend/logs/backend.log
    ```

- **Frontend**:
    Check browser console (F12) for network errors.

### Enabling Debug Logging

Set log level to DEBUG for verbose output:

```bash
# In .env
LOG_LEVEL=DEBUG

# Or via API (requires admin)
curl -X PUT http://localhost:8000/api/v1/observability/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"log_level": "DEBUG"}'
```

### Testing Observability

Emit a test log to verify logging is working:

```bash
curl -X POST "http://localhost:8000/api/v1/observability/test-log?level=INFO&message=Test" \
  -H "Authorization: Bearer $TOKEN"
```

### Inspecting Langfuse Traces

1. Open Langfuse dashboard: http://localhost:3001
2. Navigate to **Traces** tab
3. Filter by time range or session ID
4. Click a trace to see full call chain, tokens, and latency

## Support

If issues persist, please open an issue on the GitHub repository with:
- Error message and stack trace
- Relevant log excerpts
- Environment details (OS, Python version, package versions)

## Related Documentation

- [Observability & Tracing](Observability.md)
- [Backend Architecture](Backend.md)
- [Deployment Guide](Deployment.md)

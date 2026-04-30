# Ingestion & Indexing Guide

This guide details the process of ingesting raw data (files and databases) into the Data Insights Copilot's vector store and SQL pipeline.

## 1. Supported Formats

The ingestion engine supports a variety of data types:

| Category | Formats | Engine |
|----------|---------|--------|
| **Structured** | PostgreSQL, MySQL, DuckDB, SQLite | SQLAlchemy Reflection |
| **Tabular Files**| `.csv`, `.xlsx`, `.parquet` | Pandas / DuckDB |
| **Documents** | `.pdf`, `.docx`, `.txt`, `.md` | PDFPlumber / Unstructured |
| **FHIR** | JSON Bundles | Custom FHIR Flattening |

## 2. Ingestion Workflow

### Step 1: Data Acquisition
- **File Upload**: Large files are streamed to `/backend/data/uploads` and metadata is recorded in PostgreSQL.
- **DB Sync**: The system connects via your provided URI and performs a `Schema Discovery` scan.

### Step 2: Extraction & Processing
The engine performs a "Delta Check" to avoid re-processing unchanged data:
- **Chunking**: Documents are split based on your configured strategy.
- **Metadata Enrichment**: Rows/Chunks are tagged with IDs, timestamps, and cross-references.
- **Normalization**: Text is cleaned of junk characters while preserving medical/technical terminology.

### Step 3: Vectorization (The Indexing Job)
The **Embeddings Module** kicks in:
1.  **Job Queueing**: A job entry is created in the `embedding_jobs` table.
2.  **Background Execution**:
    -   Small jobs run using the `ThreadPoolExecutor`.
    -   Large/Periodic jobs are dispatched to **Celery Beat**.
3.  **Vector Storage**: Normalized embeddings are pushed to **Qdrant** in agent-specific collections.

## 3. Monitoring Progress

You can track ingestion via the UI or the API:

- **UI Progress Bar**: Shows percentage, ETA, and throughput (docs/sec).
- **API Polling**: `GET /api/v1/embeddings/jobs/{job_id}`
- **Log Inspection**: Check `backend.log` for details on batch failures or retries.

## 4. Advanced: Schema Discovery Fallback

In highly restricted database environments, the standard SQLAlchemy reflection might fail (e.g., `InsufficientPrivilege` on system catalogs).

**How we handle it:**
The Ingestion Module includes a **Raw SQL Fallback**. If a metadata scan fails, it automatically executes queries against `information_schema.columns` and `information_schema.key_column_usage` to rebuild the schema graph manually.

## 5. Troubleshooting Ingestion

-   **"Dimension Mismatch"**: Ensure the embedding model selected in Step 2 of the Agent Wizard matches the model used for existing vectors. If you change models, a **Full Re-index** is mandatory.
-   **"Connection Timeout"**: Check your database's `max_connections` and ensure the backend's connection pool is not exhausted.
-   **"Stale Data"**: If the source data changes but the AI still reports old info, ensure the "Delta Check" is not incorrectly skipping files. Use **Force Re-index** as a fallback.

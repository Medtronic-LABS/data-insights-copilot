# Database Infrastructure

The Data Insights Copilot uses a multi-layered database architecture to balance structured configuration, audit logs, and high-dimensional vector search.

## Primary Database (PostgreSQL)

The core application state, user accounts, agent configurations, and audit logs are stored in **PostgreSQL**. The backend uses **SQLAlchemy 2.0** with the `asyncpg` driver for high-performance asynchronous access.

### Connection Pooling
To prevent connection exhaustion and ensure stability during concurrent dashboard synthesis, the system implements a robust connection pooling layer:

| Setting | Default Value | Description |
|---------|---------------|-------------|
| `pool_size` | 10 | The number of permanent connections kept in the pool. |
| `max_overflow` | 20 | Additional temporary connections allowed during peak load. |
| `pool_timeout` | 30s | Max time to wait for a connection from the pool before timing out. |
| `pool_recycle` | 3600s | Periodically recycles connections to prevent stale sockets. |
| `health_check` | 30s | Background loop that verifies connection health and auto-reconnects if required. |

## Vector Database (Qdrant)

High-dimensional embeddings for RAG are stored in **Qdrant**. This enables semantic search across ingested documents and database schemas.

### Vector Collection Isolation
Each agent config gets a dedicated vector collection to ensure dimension safety and semantic isolation:
- **Naming Pattern**: `agent_{agent_id}_config_{config_id}`
- **Isolation Policy**: Each collection is independent; changing one agent's embedding model or chunking strategy does not affect other agents.
- **Cleanup**: collections are automatically purged and recreated during full re-indexing jobs.

---

## Core Tables (PostgreSQL)

These tables are managed via **Alembic** migrations and reside in the `public` schema.

### `users`
Stores user accounts and authentication details.
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Unique user ID. |
| `email` | VARCHAR UNIQUE | User email (used for login). |
| `hashed_password` | VARCHAR | Argon2/Bcrypt password hash. |
| `full_name` | VARCHAR | Display name. |
| `role` | VARCHAR | Role (`admin`, `user`, `viewer`). |
| `is_active` | BOOLEAN | Account status. |

### `agent_configs`
The central configuration for an AI Agent.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Config ID. |
| `agent_id` | UUID | FK to the parent Agent. |
| `data_source_id` | UUID | FK to the connected data source. |
| `embedding_model_id` | UUID | FK to the selected embedding model in AI Registry. |
| `llm_model_id` | UUID | FK to the selected LLM in AI Registry. |
| `chunking_config` | JSONB | Settings for parent/child chunking and overlap. |
| `rag_config` | JSONB | Retrieval settings (top_k, threshold). |
| `vector_collection_name` | VARCHAR | Link to the Qdrant collection. |
| `embedding_status` | VARCHAR | `not_started`, `in_progress`, `completed`, `failed`. |

### `embedding_jobs`
Tracks the lifecycle of background indexing tasks.
| Column | Type | Description |
|--------|------|-------------|
| `job_id` | VARCHAR PK | Unique ID (e.g., `emb-job-...`). |
| `status` | VARCHAR | `QUEUED`, `PREPARING`, `EMBEDDING`, `COMPLETED`, `FAILED`. |
| `total_documents` | INTEGER | Estimated total docs for the job. |
| `processed_documents`| INTEGER | Progress counter. |
| `error_message` | TEXT | Failure details for troubleshooting. |
| `started_at` | TIMESTAMP | Job start time. |

---


## System Settings (Migration 006)

### `system_settings`
Key-value store for application configuration (UI, Auth, LLM settings).
| Column | Type | Description |
|--------|------|-------------|
| `category` | TEXT | Group (e.g., `llm`, `auth`). |
| `key` | TEXT | Setting key. |
| `value` | TEXT | JSON-encoded value. |
| `value_type` | TEXT | `string`, `number`, `boolean`, `secret`. |
| `is_sensitive` | INTEGER | 1 if value should be masked (e.g., API keys). |

### `settings_history`
Audit trail for setting changes.
| Column | Type | Description |
|--------|------|-------------|
| `setting_id` | INTEGER | FK to `system_settings`. |
| `previous_value` | TEXT | Value before change. |
| `new_value` | TEXT | Value after change. |
| `changed_by` | TEXT | Username of modifier. |

---

## Notifications (Migration 002)

### `notifications`
In-app notifications for users.
| Column | Type | Description |
|--------|------|-------------|
| `user_id` | INTEGER | Recipient. |
| `type` | TEXT | Event type. |
| `title` | TEXT | Notification title. |
| `status` | TEXT | `unread`, `read`. |

### `notification_preferences`
User settings for notification channels.
| Column | Type | Description |
|--------|------|-------------|
| `user_id` | INTEGER | User ID. |
| `email_enabled` | INTEGER | 1 = Enabled. |
| `webhook_url` | TEXT | Optional Slack/Teams webhook. |

# Database Schema

The Data Insights Copilot uses **SQLite** as its primary database (`app.db`). The schema is managed via a custom migration system.

## Core Tables

These tables are initialized by the application core.

### `users`
Stores user accounts and authentication details.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-incrementing user ID. |
| `username` | TEXT UNIQUE | Unique username for login. |
| `email` | TEXT UNIQUE | User email address. |
| `password_hash` | TEXT | Bcrypt password hash. |
| `full_name` | TEXT | Display name. |
| `role` | TEXT | Role (`super_admin`, `editor`, `user`, `viewer`). |
| `is_active` | INTEGER | 1 = Active, 0 = Deactivated. |
| `created_at` | TIMESTAMP | Creation time. |

### `system_prompts`
Versioned history of the system prompt used by the Agent.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Prompt ID. |
| `prompt_text` | TEXT | The actual prompt template. |
| `version` | INTEGER | Version number. |
| `is_active` | INTEGER | 1 if this is the currently active prompt. |
| `created_by` | TEXT | Username of creator. |

### `prompt_configs`
Configuration associated with a specific system prompt version.
| Column | Type | Description |
|--------|------|-------------|
| `prompt_id` | INTEGER PK | FK to `system_prompts.id`. |
| `connection_id` | INTEGER | FK to `db_connections.id` (if data_source_type is 'database'). |
| `data_source_type` | TEXT | Source type for this agent ('database' or 'file'). |
| `schema_selection` | TEXT | JSON list of enabled tables. |
| `data_dictionary` | TEXT | Markdown data dictionary content. |
| `reasoning` | TEXT | JSON configuration for reasoning steps. |
| `example_questions` | TEXT | JSON list of few-shot examples. |
| `ingestion_documents` | TEXT | JSON list of extracted document sections. |
| `ingestion_file_name` | TEXT | Original uploaded filename. |
| `ingestion_file_type` | TEXT | Extracted file extension (e.g. 'pdf'). |

### `db_connections`
External database connections that the Agent can query.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Connection ID. |
| `name` | TEXT | Unique display name. |
| `uri` | TEXT | SQLAlchemy connection string. |
| `engine_type` | TEXT | Database type (e.g., `postgresql`). |

---

## RAG & Embeddings (Migrations 001, 003)

### `rag_configurations`
Stores complete configuration snapshots for reproducibility.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Config ID. |
| `version` | TEXT | Semantic version (e.g., "1.0.0"). |
| `status` | TEXT | `draft`, `published`, `archived`. |
| `schema_snapshot` | TEXT | JSON snapshot of schema at time of creation. |
| `config_hash` | TEXT | SHA-256 hash for integrity. |

### `embedding_jobs`
Tracks background embedding generation jobs.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Internal ID. |
| `job_id` | TEXT UNIQUE | Public Job ID (e.g., `emb-job-...`). |
| `status` | TEXT | `QUEUED`, `EMBEDDING`, `COMPLETED`, `FAILED`. |
| `total_documents` | INTEGER | Total docs to process. |
| `progress_percentage` | REAL | 0.0 to 100.0. |

### `embedding_versions`
Links a RAG configuration to a specific set of generated embeddings.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Version ID. |
| `embedding_model` | TEXT | Model used (e.g., `BAAI/bge-m3`). |
| `embedding_dimension` | INTEGER | Vector size (e.g., 1024). |

---

## Per-Agent Embedding Configuration (Migration 019)

These tables support per-agent embedding model configuration, allowing different agents to use different embedding models (e.g., one agent using BGE-M3, another using OpenAI embeddings).

### `agent_embedding_configs`
Stores the embedding model configuration for each agent.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Config ID. |
| `agent_id` | INTEGER UNIQUE | FK to `agents.id`. |
| `provider` | TEXT | Embedding provider (`sentence-transformers`, `openai`, `bge-m3`). |
| `model_name` | TEXT | Model identifier (e.g., `BAAI/bge-m3`, `text-embedding-3-small`). |
| `model_path` | TEXT | Local path for downloaded models. |
| `dimension` | INTEGER | Vector dimension (e.g., 1024, 1536). |
| `batch_size` | INTEGER | Batch size for embedding generation. |
| `collection_name` | TEXT | Qdrant collection name (format: `agent_{id}_{model_hash}`). |
| `last_embedded_at` | TIMESTAMP | Last successful embedding run. |
| `document_count` | INTEGER | Number of documents indexed. |
| `requires_reindex` | INTEGER | 1 if model changed and reindex needed. |

### `agent_embedding_history`
Audit trail for embedding model changes per agent.
| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | History ID. |
| `agent_id` | INTEGER | FK to `agents.id`. |
| `previous_provider` | TEXT | Previous provider before change. |
| `previous_model` | TEXT | Previous model name. |
| `previous_dimension` | INTEGER | Previous vector dimension. |
| `new_provider` | TEXT | New provider after change. |
| `new_model` | TEXT | New model name. |
| `new_dimension` | INTEGER | New vector dimension. |
| `change_reason` | TEXT | Reason for the change. |
| `changed_by` | TEXT | Username who made the change. |
| `changed_at` | TIMESTAMP | When the change occurred. |
| `reindex_triggered` | INTEGER | 1 if reindexing was triggered. |
| `reindex_job_id` | TEXT | Job ID of the reindex operation. |

### Important: Vector Collection Isolation

Each agent gets its own vector collection in Qdrant, named using the pattern:
```
agent_{agent_id}_{model_hash_8chars}
```

This ensures:
- **Dimension safety**: Different models with different dimensions don't conflict
- **Semantic isolation**: Embeddings from different models stay in separate vector spaces
- **Independent reindexing**: Changing one agent's model doesn't affect others

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

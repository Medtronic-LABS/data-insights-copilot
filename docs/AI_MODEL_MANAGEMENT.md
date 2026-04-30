# AI Model Management Guide

This guide covers the management of LLM (Large Language Model) and Embedding providers within the Data Insights Copilot.

## 1. Unified Model Registry

The system uses a **Unified Model Registry** (`app/modules/ai_models`) to abstract away the differences between cloud-based and local models.

### API-Based Providers (Cloud)
These models require an external API key and internet connectivity.
- **OpenAI**: GPT-4o, GPT-4o-mini, text-embedding-3-small.
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus.
- **Azure OpenAI**: Enterprise-grade deployments with custom endpoints.

### Local Providers (On-Prem/Edge)
These models run directly on your hardware (CPU or GPU).
- **Ollama**: Supports Llama 3, Mistral, and other GGUF models.
- **HuggingFace (SentenceTransformers)**: For high-performance local embeddings like BGE-M3.
- **LlamaCpp**: Direct execution of GGUF files.

## 2. Managing Models via UI

Navigate to **Settings → AI Registry** to manage your models.

### Adding an API Provider
1.  Select the **Provider Type** (e.g., Anthropic).
2.  Enter your **API Key**.
3.  Click **Fetch Models** to see available options for that account.
4.  Toggle **Enabled** on the models you wish to expose to the Agent Wizard.

### Downloading Local Models
1.  Navigate to the **Local Models** tab.
2.  Search by name or HuggingFace ID (e.g., `BAAI/bge-m3`).
3.  Click **Download**. The system will start a background `Job` to pull the weights.
4.  **Monitor Progress**: View the download throughput and disk usage in the registry dashboard.
5.  Once complete, the model will be available for use in agent configurations.

## 3. Setting System Defaults

You can define which models are used for newly created agents in `app/core/config/defaults.py`.

- **Default Inference**: GPT-4o-mini (recommended for speed/cost).
- **Default Embedding**: text-embedding-3-small (Cloud) or BGE-M3 (Local).

## 4. Model Switching (Hot-Swap)

The Data Insights Copilot supports **Runtime Hot-Swapping**:
- You can change the model used by a published agent by editing its configuration and clicking "Re-publish".
- **Warning**: Changing the **Embedding Model** requires a full re-indexing of the data source, as vector dimensions and semantic spaces differ between models.

## 5. Troubleshooting Model Issues

-   **"Model Not Found"**: Ensure the model name exactly matches the provider's ID (e.g., `gpt-4o-mini` instead of just `GPT4`).
-   **"Resource Exhausted"**: Usually a rate limit from OpenAI/Anthropic. Check your billing status or consider switching to a local model.
-   **"HuggingFace Timeout"**: Large model downloads can take time. Ensure the server has a stable internet connection and sufficient disk space in `/backend/data/models`.

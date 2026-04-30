# Agent Creation Guide

This guide provides a step-by-step walk-through for creating and configuring a new AI Agent in the Data Insights Copilot.

## 1. Connect a Data Source

The first step in creating an agent is defining what data it will have access to.

1.  Navigate to **Data Sources** in the sidebar.
2.  Click **+ Add Data Source**.
3.  Choose your source type:
    -   **Database**: For structured insights from PostgreSQL, MySQL, etc. Provide the connection URI (e.g., `postgresql+asyncpg://user:pass@host:port/dbname`).
    -   **Files**: For unstructured context from PDFs, CSVs, or Excel files.
4.  **Verify Connection**: Click "Test Connection" to ensure connectivity.
5.  **Schema Discovery**: Once connected, the system will automatically discover the schema. You can manually trigger a "Refresh Schema" if the DB changes.

## 2. Configure the Agent Wizard

Once you have a data source, you can build an agent using the configuration wizard.

1.  Navigate to **Agents** and click **Create Agent**.
2.  **Step 1: Identity**: Give your agent a name and description (e.g., "Clinical Audit Bot").
3.  **Step 2: Data Source**: Select the data source you connected in Step 1.
4.  **Step 3: Intent Routing**:
    -   If using a Database, the system will ask which tables the agent should "own".
    -   **Tip**: Select only the tables relevant to the agent's purpose to minimize LLM confusion.
5.  **Step 4: System Prompt**:
    -   The system provides a **Base Template**. 
    -   You can customize the "Operational Instructions" (e.g., "You are an expert medical coder...").
    -   **Context Injection**: The wizard will automatically inject selected schema metadata into the prompt.
6.  **Step 5: Model Selection**:
    -   Select an **Inference Model** (e.g., GPT-4o-mini).
    -   Select an **Embedding Model** (e.g., Qdrant-optimized BGE-M3) for RAG support.
7.  **Step 6: RAG & Chunking** (for Files):
    -   Configure the **Chunking Strategy** (Parent/Child is recommended for medical documents).
    -   Set the **Similarity Threshold** for retrieval.

## 3. Training & Indexing (The "Double Check")

Before deployment, your agent needs to index its data.

1.  **Trigger Indexing**: Click **Start Indexing** in the agent dashboard.
2.  **Monitor Progress**: View the real-time progress bar. The system uses a dual-task model:
    -   **Metadata Extraction**: Fast, runs in-process.
    -   **Vector Embedding**: Intensive, managed by the background job executor (or Celery Beat if scheduled).
3.  **Validation**: Once completion reaches 100%, the agent is ready for chat.

## 4. Testing & Publishing

1.  **Test in Playground**: Use the side-panel chat to verify the agent's logic.
2.  **Inspecting Chains**: Use the **QA Debug** toggle to view the internal SQL reflection loop and retrieval chunks.
3.  **Publish**: Once satisfied, click **Publish Version**. This creates an immutable snapshot of the configuration.

## 5. Maintenance

-   **Re-indexing**: If you upload new files or the DB schema evolves significantly, use the "Force Re-index" button.
-   **Config Evolution**: You can edit a published agent, which will create a new "Draft" version until you choose to publish again.

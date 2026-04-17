# Step-by-Step Setup Guide

This guide provides a definitive path for setting up the Data Insights Copilot in local and Docker environments.

## 1. Environment Preparation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Medtronic-LABS/data-insights-copilot.git
    cd data-insights-copilot
    ```

2.  **Environment Variables**:
    Copy the example file and fill in your keys.
    ```bash
    cp .env.example .env
    ```
    **Critical Keys**:
    - `OPENAI_API_KEY`: Required for default AI operations.
    - `POSTGRES_ASYNC_URI`: Should point to a valid PostgreSQL instance.
    - `QDRANT_URL`: Required for Vector RAG.

## 2. Option A: Docker Compose (Recommended)

This is the fastest way to get all infrastructure (PostgreSQL, Qdrant, Redis, RabbitMQ, Langfuse) running.

```bash
docker compose up -d
```

**Services will be available at:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Langfuse**: http://localhost:3001
- **Qdrant**: http://localhost:6333

## 3. Option B: Local Development (Manual)

Use this if you need to debug the Python backend or React frontend directly.

### Step 1: Infrastructure
Ensure PostgreSQL and Qdrant are running (you can use Docker for just these):
```bash
docker run -p 5432:5432 -e POSTGRES_PASSWORD=admin postgres:16
docker run -p 6333:6333 qdrant/qdrant
```

### Step 2: Backend Setup
1.  **Create Conda Environment**:
    ```bash
    conda create -n data-insights-copilot python=3.10
    conda activate data-insights-copilot
    ```
2.  **Install Dependencies**:
    ```bash
    cd backend
    pip install -r requirements.txt
    ```
3.  **Run Migrations**:
    ```bash
    alembic upgrade head
    ```
4.  **Start Dev Server**:
    ```bash
    ./run_dev.sh
    ```

### Step 3: Frontend Setup
1.  **Install Deps**:
    ```bash
    npm install
    ```
2.  **Start Vite**:
    ```bash
    npm run dev
    ```

## 4. Post-Setup Checklist

1.  **Login**: Use `admin` / `admin123`.
2.  **AI Registry**: Go to Settings and ensure at least one LLM and one Embedding model are connected and "Enabled".
3.  **Data Source**: Connect your first database or upload a file.
4.  **Agent Creation**: Follow the [Agent Creation Guide](AGENT_CREATION_GUIDE.md) to build your first AI assistant.

## 5. Troubleshooting Setup

-   **"Command Not Found"**: Ensure `conda`, `docker`, and `npm` are in your PATH.
-   **"Port Already in Use"**: Check if another service is using 8000, 3000, or 5432. Fix by stopping the other service or changing the port in `.env`.
-   **"CORS Error"**: Ensure `CORS_ORIGINS` in `.env` includes your local development URL (e.g., `http://localhost:5173`).

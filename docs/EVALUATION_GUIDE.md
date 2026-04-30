# Evaluation Framework Guide

This guide describes how to run and interpret the evaluation framework to measure the accuracy and performance of the Data Insights Copilot's RAG and SQL pipelines.

## 1. Overview

The evaluation system uses a "Golden Dataset" approach to benchmark the AI against known correct answers. It measures:
- **SQL Accuracy**: Exact match and semantic similarity of generated queries.
- **RAG Metrics (RAGAS)**: Context precision, faithfulness, and answer relevancy.
- **Latency**: End-to-end response time.

## 2. Setting Up the Golden Dataset

The dataset typically resides in `eval/golden_dataset.json`. Each entry should include:
- `question`: The natural language user query.
- `reference_sql`: The correct SQL query (for SQL eval).
- `reference_context`: The expected document snippets (for RAG eval).
- `reference_answer`: The definitive natural language answer.

## 3. Running SQL Evaluations

Use the standalone script to test the NL2SQL pipeline:

```bash
conda run -n data-insights-copilot python scripts/run_eval.py --type sql --dataset eval/golden_dataset.json
```

**What it does:**
1.  Iterates through the dataset.
2.  Generates SQL using the current agent configuration.
3.  Executes the generated SQL against the test database.
4.  Compares results with `reference_sql` execution results.
5.  Calculates the **Success Rate** and **Execution Time**.

## 4. Running RAG Evaluations (RAGAS)

For document-based agents, we use the **RAGAS** framework:

```bash
conda run -n data-insights-copilot python scripts/run_eval.py --type rag --dataset eval/golden_dataset.json
```

**Key Metrics:**
- **Faithfulness**: Is the answer derived solely from the retrieved context?
- **Answer Relevancy**: Does the answer address the user's queston?
- **Context Precision**: How many of the top retrieved chunks are actually relevant?

## 5. Interpreting Results

The framework generates a report in `eval/reports/eval_{timestamp}.html`.

- **Score > 0.9**: Production-ready.
- **Score 0.7 - 0.9**: Needs refinement (check system prompts or chunking strategy).
- **Score < 0.7**: Critical failures (usually due to bad schema mapping or poor data quality).

## 6. Automating Evals

It is highly recommended to run evaluations as part of your CI/CD pipeline or before publishing a new **System Prompt** version to ensure no regression in answer quality.

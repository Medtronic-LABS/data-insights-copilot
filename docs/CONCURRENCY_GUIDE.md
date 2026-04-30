# Concurrency & Performance Guide

This guide explains the technical architecture used by Data Insights Copilot to handle parallel AI operations and prevent timeout errors.

## 1. The Challenge

Generating an AI dashboard often requires executing multiple independent SQL queries and vector searches simultaneously. Standard asynchronous FastAPI code can run into issues when integrating with blocking database drivers or thread-unsafe AI libraries, leading to the dreaded `ERR_EMPTY_RESPONSE` or query timeouts.

## 2. The Solution: Async-to-Sync Bridge

The `SQLService` (within `app/modules/chat`) implements a specialized bridge to handle high-concurrency workloads.

### How it Works:
1.  **Intent Detection**: The main FastAPI event loop receives the request.
2.  **Parallel Dispatch**: If the request is for a dashboard, the agent dispatches multiple sub-tasks.
3.  **Isolation**: Each sub-task is executed in a dedicated thread managed by a `ThreadPoolExecutor`.
4.  **Async-to-Sync Wrapper**: Since SQLAlchemy and certain LLM calls might hold specific locks, we wrap these calls in a bridge that ensures they don't block the main event loop while maintaining thread safety.
5.  **Result Aggregation**: Once all threads complete, the main loop aggregates the results into a single JSON response.

## 3. Database Connection Pooling

To support this parallel execution, the system uses **SQLAlchemy QueuePool**:

- **Default Pool Size**: 10
- **Max Overflow**: 20
- **Recycle Rate**: 1 hour

This ensures that even during heavy dashboard synthesis, the system has enough ready-to-use connections to satisfy all parallel sub-queries without the overhead of creating new TCP connections for every request.

## 4. Thread-Safe SQL Reflection

The "Reflection" loop (which validates SQL accuracy) is also fully thread-safe. Multiple agents can perform reflection simultaneously on different schemas without clashing, as each session is isolated at the `AsyncSession` level.

## 5. Performance Tuning

If you experience latency or timeouts in high-traffic environments:

1.  **Increase Thread Pool**: Adjust `MAX_WORKERS` in `app/core/config/settings.py`.
2.  **Optimize DB**: Ensure index coverage on columns used frequently in natural language queries.
3.  **Reduce Embedding Batch Size**: If embedding jobs are slow, reduce the batch size in the Agent Wizard to prevent VRAM/RAM contention.

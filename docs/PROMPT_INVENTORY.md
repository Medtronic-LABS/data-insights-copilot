# Hardcoded Prompts Inventory & Modularization Guide

This document catalogs all hardcoded prompts in the codebase and provides a rationalization for modularization, reuse, and maintainability.

## 1. Current State: Centralized Prompt System

The project already has a centralized prompt loading system in place:

- **Loader**: `backend/app/core/prompts.py`
- **Templates**: `agent_spec/prompt_templates/*.md`

### Existing Template Files
| Template | File | Loader Function |
|----------|------|-----------------|
| SQL Generator | `sql_generator.md` | `get_sql_generator_prompt()` |
| Intent Router | `intent_router.md` | `get_intent_router_prompt()` |
| Follow-up Generator | `followup_generator.md` | `get_followup_generator_prompt()` |
| Data Analyst | `data_analyst.md` | `get_data_analyst_prompt()` |
| RAG Synthesis | `rag_synthesis.md` | `get_rag_synthesis_prompt()` |
| Chart Generator | `chart_generator.md` | `get_chart_generator_prompt()` |
| Query Planner | `query_planner.md` | `get_query_planner_prompt()` |
| Reflection Critique | `reflection_critique.md` | `get_reflection_critique_prompt()` |
| Query Rewriter | `query_rewriter.md` | `get_query_rewriter_prompt()` |
| Base System | `base_system.md` | `get_base_system_prompt()` |
| Database Generator | `database_generator.md` | `get_database_generator_prompt()` |
| File Generator | `file_generator.md` | `get_file_generator_prompt()` |
| Reasoning Generator | `reasoning_generator.md` | `get_reasoning_generator_prompt()` |
| DuckDB SQL Rules | `duckdb_sql_rules.md` | `get_duckdb_sql_rules_prompt()` |
| Query Relevance | `query_relevance.md` | `get_query_relevance_prompt()` |

---

## 2. Identified Hardcoded Prompts (Requiring Extraction)

### A. SQL Correction Prompt
**Location**: `backend/app/modules/chat/sql_executor.py` (lines 422-455)
**Classification**: SQL Error Correction
**Status**: ✅ Extracted to `sql_correction.md`

### B. SQL Fix Hints
**Location**: `backend/app/modules/chat/query/query_validation_layer.py` (lines 293-350)
**Classification**: Error-specific fix hints
**Status**: ✅ Extracted to `sql_fix_hints.md`

### C. Result Formatter Prompt
**Location**: `backend/app/modules/chat/file_sql_service.py` (lines 636-670)
**Classification**: Response formatting with charts
**Status**: ✅ Extracted to `result_formatter.md`

### D. Dialect-Specific Rules
**Location**: `backend/app/core/prompt_templates.py` (lines 67-113)
**Classification**: SQL dialect rules
**Status**: ✅ Extracted to `dialects/postgresql_rules.md`, `dialects/duckdb_rules.md`

### E. Default System Prompts
**Location**: `backend/app/core/config/defaults.py` (lines 139-175)
**Classification**: System defaults for new agents
**Action Required**: Consider extracting to `defaults/` directory

### F. DuckDB Constraints Fallback
**Location**: `backend/app/modules/chat/file_sql_service.py` (lines 51-58)
**Classification**: DuckDB-specific rules
**Status**: Should use `get_duckdb_sql_rules_prompt()` instead

### G. PromptBuilder Inline Constraints
**Location**: `backend/app/modules/chat/query/prompt_builder.py` (lines 130-195)
**Classification**: SQL generation constraints
**Action Required**: Extract to separate template or use dialect loader

### H. Query Relevance Fallback
**Location**: `backend/app/modules/chat/query/query_relevance_checker.py` (lines 36-53)
**Classification**: Query classification
**Status**: Already has fallback mechanism via `load_prompt()`

---

## 3. New Template Files Created

| Template | Path | Purpose |
|----------|------|---------|
| SQL Correction | `sql_correction.md` | Fix failed SQL queries |
| SQL Fix Hints | `sql_fix_hints.md` | Error-type specific hints |
| Result Formatter | `result_formatter.md` | NL response with charts |
| PostgreSQL Rules | `dialects/postgresql_rules.md` | PostgreSQL-specific syntax |
| DuckDB Rules | `dialects/duckdb_rules.md` | DuckDB-specific syntax |

---

## 4. New Loader Functions Added

Add these to `backend/app/core/prompts.py`:

```python
def get_sql_correction_prompt() -> str:
    """Get the SQL correction/debugging prompt."""
    return load_prompt("sql_correction", fallback="...")

def get_sql_fix_hints_prompt() -> str:
    """Get the SQL fix hints by error type."""
    return load_prompt("sql_fix_hints", fallback="...")

def get_result_formatter_prompt() -> str:
    """Get the result formatter prompt."""
    return load_prompt("result_formatter", fallback="...")

def get_dialect_rules_prompt(dialect: str) -> str:
    """Get dialect-specific SQL rules."""
    dialect_map = {
        "postgresql": "dialects/postgresql_rules",
        "duckdb": "dialects/duckdb_rules",
    }
    return load_prompt(dialect_map.get(dialect, "dialects/postgresql_rules"))
```

---

## 5. Recommended Directory Structure

```
agent_spec/prompt_templates/
├── base/
│   ├── base_system.md
│   └── healthcare_context.md
├── sql/
│   ├── sql_generator.md
│   ├── sql_correction.md
│   ├── sql_fix_hints.md
│   └── query_planner.md
├── dialects/
│   ├── postgresql_rules.md
│   ├── duckdb_rules.md
│   ├── mysql_rules.md
│   └── sqlserver_rules.md
├── classification/
│   ├── intent_router.md
│   ├── query_relevance.md
│   └── query_rewriter.md
├── response/
│   ├── result_formatter.md
│   ├── chart_generator.md
│   ├── data_analyst.md
│   └── followup_generator.md
├── rag/
│   ├── rag_synthesis.md
│   └── reasoning_generator.md
└── validation/
    └── reflection_critique.md
```

---

## 6. Migration Checklist

### Phase 1: Template Extraction (Completed)
- [x] Create `sql_correction.md`
- [x] Create `sql_fix_hints.md`
- [x] Create `result_formatter.md`
- [x] Create `dialects/postgresql_rules.md`
- [x] Create `dialects/duckdb_rules.md`

### Phase 2: Code Updates (Pending)
- [ ] Update `sql_executor.py` to use `get_sql_correction_prompt()`
- [ ] Update `query_validation_layer.py` to use `get_sql_fix_hints_prompt()`
- [ ] Update `file_sql_service.py` to use `get_result_formatter_prompt()`
- [ ] Update `prompt_templates.py` to use `get_dialect_rules_prompt()`
- [ ] Update `prompt_builder.py` to use centralized dialect rules

### Phase 3: Testing
- [ ] Verify all prompts load correctly
- [ ] Run SQL generation tests
- [ ] Run correction/retry tests
- [ ] Verify chart generation still works

---

## 7. Benefits of Modularization

1. **Single Source of Truth**: All prompts in one directory
2. **Easy Updates**: Change prompts without touching code
3. **Version Control**: Track prompt changes in git
4. **A/B Testing**: Easily swap prompt variants
5. **Consistency**: Reuse common patterns across features
6. **Documentation**: Markdown format is self-documenting
7. **Hot Reload**: Use `clear_prompt_cache()` for testing

---

## 8. Usage Examples

### Loading a Prompt
```python
from app.core.prompts import load_prompt, get_sql_correction_prompt

# Direct load
prompt = load_prompt("sql_correction")

# Via convenience function
prompt = get_sql_correction_prompt()

# With fallback
prompt = load_prompt("custom_prompt", fallback="Default text")
```

### Clearing Cache (for development)
```python
from app.core.prompts import clear_prompt_cache

clear_prompt_cache()  # Reload all prompts from disk
```

### Using Dialect Rules
```python
from app.core.prompts import get_dialect_rules_prompt

rules = get_dialect_rules_prompt("duckdb")
rules = get_dialect_rules_prompt("postgresql")
```

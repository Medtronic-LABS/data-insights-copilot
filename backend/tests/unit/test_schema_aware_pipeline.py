"""
Unit tests for the schema-aware SQL pipeline components.

Tests SchemaGraph, DataDictionary, SchemaLinker, QueryPlanner, and PromptBuilder
using mocked database engines and LLM responses.
"""
import pytest
import os
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

# Set test environment
os.environ["OPENAI_API_KEY"] = "test-key-123"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-chars-long-for-jwt-signing"


# =============================================================================
# DataDictionary Tests
# =============================================================================

class TestDataDictionary:
    """Tests for DataDictionary business-logic layer."""
    
    def setup_method(self):
        from backend.services.data_dictionary import DataDictionary
        # Load from actual config file
        config_path = Path(__file__).parent.parent.parent / "config" / "data_dictionary.yaml"
        self.dd = DataDictionary(config_path=str(config_path))
    
    def test_load_synonyms(self):
        """Test that synonyms are loaded from YAML."""
        assert len(self.dd._synonyms) > 0
        # 'patients' should map to a table name string
        assert 'patients' in self.dd._synonyms
    
    def test_resolve_synonym(self):
        """Test synonym resolution returns table name."""
        result = self.dd.resolve_synonym("patients")
        assert result is not None
        assert result == "patient_tracker"
    
    def test_resolve_unknown_synonym(self):
        """Test that unknown terms return None."""
        result = self.dd.resolve_synonym("xyznonexistent")
        assert result is None
    
    def test_get_default_filters(self):
        """Test default filter retrieval for a table."""
        filters = self.dd.get_default_filters("patient_tracker")
        assert isinstance(filters, list)
        assert len(filters) > 0
        # Filters are strings like "is_active = true"
        assert any("is_active" in f for f in filters)
        assert any("is_deleted" in f for f in filters)
    
    def test_get_default_filters_unknown_table(self):
        """Test default filters for unknown table returns empty."""
        filters = self.dd.get_default_filters("nonexistent_table")
        assert filters == []
    
    def test_resolve_business_term(self):
        """Test business term resolution via resolve_term."""
        defn = self.dd.resolve_term("active patient")
        assert defn is not None
        assert "table" in defn or "condition" in defn
    
    def test_to_prompt_context(self):
        """Test prompt context generation."""
        ctx = self.dd.to_prompt_context(["patient_tracker"])
        assert isinstance(ctx, str)
        assert len(ctx) > 0
    
    def test_to_prompt_context_empty_tables(self):
        """Test prompt context with no matching tables."""
        ctx = self.dd.to_prompt_context([])
        assert isinstance(ctx, str)


# =============================================================================
# PromptBuilder Tests
# =============================================================================

class TestPromptBuilder:
    """Tests for PromptBuilder prompt assembly."""
    
    def setup_method(self):
        from backend.services.prompt_builder import PromptBuilder
        self.builder = PromptBuilder()
    
    def test_build_basic_postgresql(self):
        """Test basic PostgreSQL prompt generation."""
        prompt = self.builder.build(
            question="How many patients?",
            schema_context="TABLE: patient_tracker (id, name, is_active)",
            dialect="postgresql"
        )
        assert "PostgreSQL" in prompt
        assert "How many patients?" in prompt
        assert "patient_tracker" in prompt
        assert "SQL Query:" in prompt
    
    def test_build_basic_duckdb(self):
        """Test basic DuckDB prompt generation."""
        prompt = self.builder.build(
            question="Count records",
            schema_context="TABLE: data (id, value)",
            dialect="duckdb"
        )
        assert "DuckDB" in prompt
        assert "Count records" in prompt
    
    def test_build_with_query_plan(self):
        """Test prompt includes query plan context."""
        prompt = self.builder.build(
            question="test",
            schema_context="TABLE: t (id)",
            query_plan_context="QUERY PLAN:\n- Entity: t\n- Metric: COUNT(id)"
        )
        assert "QUERY PLAN" in prompt
    
    def test_build_with_data_dictionary(self):
        """Test prompt includes data dictionary context."""
        prompt = self.builder.build(
            question="test",
            schema_context="TABLE: t (id)",
            data_dictionary_context="DEFAULT FILTERS: is_active = true"
        )
        assert "DEFAULT FILTERS" in prompt
    
    def test_build_with_few_shot(self):
        """Test prompt includes few-shot examples."""
        examples = [
            "Q: How many users? SQL: SELECT COUNT(*) FROM users;",
            "Q: User names? SQL: SELECT name FROM users;"
        ]
        prompt = self.builder.build(
            question="test",
            schema_context="TABLE: t (id)",
            few_shot_examples=examples
        )
        assert "RELEVANT SQL EXAMPLES" in prompt
        assert "How many users?" in prompt
    
    def test_build_with_system_rules(self):
        """Test prompt includes system prompt rules."""
        prompt = self.builder.build(
            question="test",
            schema_context="TABLE: t (id)",
            system_prompt_rules="ALWAYS use patient_tracker not patient"
        )
        assert "patient_tracker" in prompt
    
    def test_build_for_file_query(self):
        """Test DuckDB file query prompt."""
        prompt = self.builder.build_for_file_query(
            question="Total sales",
            schema_context="TABLE: sales (id, amount)"
        )
        assert "DuckDB" in prompt
        assert "Total sales" in prompt
    
    def test_build_fix_prompt(self):
        """Test fix/correction prompt."""
        prompt = self.builder.build_fix_prompt(
            question="Count patients",
            previous_sql="SELECT COUNT(*) FROM patient",
            error_or_critique="Table 'patient' does not exist. Use 'patient_tracker'.",
            schema_context="TABLE: patient_tracker (id, name)"
        )
        assert "invalid" in prompt.lower() or "fix" in prompt.lower()
        assert "patient_tracker" in prompt
        assert "Count patients" in prompt
    
    def test_build_constraints_postgresql(self):
        """Test that PostgreSQL constraints are included."""
        prompt = self.builder.build(
            question="test",
            schema_context="TABLE: t (id)",
            dialect="postgresql"
        )
        assert "ILIKE" in prompt or "ilike" in prompt.lower()
        assert "STRICT RULES" in prompt
    
    def test_build_constraints_duckdb(self):
        """Test that DuckDB constraints are included."""
        prompt = self.builder.build(
            question="test",
            schema_context="TABLE: t (id)",
            dialect="duckdb"
        )
        assert "ILIKE" in prompt or "ilike" in prompt.lower()


# =============================================================================
# QueryPlan Model Tests
# =============================================================================

class TestQueryPlanModels:
    """Tests for Pydantic query plan models."""
    
    def test_create_simple_plan(self):
        from backend.models.query_plan import (
            QueryPlan, Metric, Filter, AggFunction, ComparisonOperator
        )
        plan = QueryPlan(
            entities=["patient_tracker"],
            metrics=[Metric(function=AggFunction.COUNT, column="id", alias="cnt")],
            filters=[Filter(column="is_active", operator=ComparisonOperator.EQ, value=True)],
            reasoning="Count active patients"
        )
        assert len(plan.entities) == 1
        assert plan.metrics[0].function == AggFunction.COUNT
        assert plan.reasoning == "Count active patients"
    
    def test_create_complex_plan(self):
        from backend.models.query_plan import (
            QueryPlan, Metric, Filter, JoinSpec, OrderSpec,
            AggFunction, ComparisonOperator
        )
        plan = QueryPlan(
            entities=["patient_tracker", "site"],
            metrics=[Metric(function=AggFunction.COUNT, column="id")],
            filters=[
                Filter(column="is_active", operator=ComparisonOperator.EQ, value=True),
                Filter(column="is_deleted", operator=ComparisonOperator.EQ, value=False),
            ],
            join_strategy=[JoinSpec(left_table="patient_tracker", left_column="site_id",
                           right_table="site", right_column="id")],
            grouping=["site.name"],
            ordering=[OrderSpec(column="cnt", direction="DESC")],
            limit=10,
            reasoning="Top 10 sites by patient count"
        )
        assert len(plan.entities) == 2
        assert len(plan.join_strategy) == 1
        assert plan.limit == 10
    
    def test_schema_link_result(self):
        from backend.models.query_plan import SchemaLinkResult, JoinPath, JoinStep
        result = SchemaLinkResult(
            tables=["patient_tracker", "site"],
            columns={"patient_tracker": ["id", "site_id"], "site": ["id", "name"]},
            join_paths=[JoinPath(
                source_table="patient_tracker",
                target_table="site",
                steps=[JoinStep(
                    from_table="patient_tracker", from_column="site_id",
                    to_table="site", to_column="id"
                )]
            )],
            confidence=0.85
        )
        assert result.confidence == 0.85
        assert len(result.join_paths) == 1


# =============================================================================
# SQLEvaluator Tests
# =============================================================================

class TestSQLEvaluator:
    """Tests for the enhanced SQL evaluator."""
    
    def setup_method(self):
        from eval.sql_eval.sql_evaluator import SQLEvaluator
        self.evaluator = SQLEvaluator(db_engine=None)
    
    def test_extract_tables(self):
        """Test table extraction from SQL."""
        tables = self.evaluator._extract_tables(
            "select * from patient_tracker pt join site s on pt.site_id = s.id"
        )
        assert "patient_tracker" in tables
        assert "site" in tables
    
    def test_check_filters_present(self):
        """Test filter compliance check — all present."""
        issues = []
        score = self.evaluator._check_filters(
            "select * from t where is_active = true and is_deleted = false",
            ["is_active", "is_deleted"],
            issues
        )
        assert score == 1.0
        assert len(issues) == 0
    
    def test_check_filters_missing(self):
        """Test filter compliance check — one missing."""
        issues = []
        score = self.evaluator._check_filters(
            "select * from t where is_active = true",
            ["is_active", "is_deleted"],
            issues
        )
        assert score == 0.5
        assert len(issues) == 1
    
    def test_check_filters_no_where(self):
        """Test filter compliance check — no WHERE clause."""
        issues = []
        score = self.evaluator._check_filters(
            "select * from t",
            ["is_active"],
            issues
        )
        assert score == 0.0
    
    def test_check_aggregations(self):
        """Test aggregation match."""
        issues = []
        score = self.evaluator._check_aggregations(
            "select count(*) from t group by name",
            ["COUNT"],
            issues
        )
        assert score == 1.0
    
    def test_check_aggregations_missing(self):
        """Test missing aggregation."""
        issues = []
        score = self.evaluator._check_aggregations(
            "select * from t",
            ["COUNT", "AVG"],
            issues
        )
        assert score == 0.0
    
    def test_evaluate_schema_only(self):
        """Test full evaluation without DB engine."""
        result = self.evaluator.evaluate_query(
            query="How many patients?",
            generated_sql="SELECT COUNT(*) FROM patient_tracker WHERE is_active = true AND is_deleted = false",
            ground_truth_sql="SELECT COUNT(*) FROM patient_tracker WHERE is_active = true AND is_deleted = false",
            expected_tables=["patient_tracker"],
            expected_filters=["is_active", "is_deleted"],
            expected_aggregations=["COUNT"]
        )
        assert result["schema_compliance"]["table_accuracy"] == 1.0
        assert result["schema_compliance"]["filter_compliance"] == 1.0
        assert result["schema_compliance"]["aggregation_match"] == 1.0
        assert result["overall_score"] > 0.9
    
    def test_evaluate_batch(self):
        """Test batch evaluation."""
        entries = [
            {
                "id": "test_001",
                "query": "Count patients",
                "generated_sql": "SELECT COUNT(*) FROM patient_tracker WHERE is_active = true",
                "ground_truth_sql": "SELECT COUNT(*) FROM patient_tracker WHERE is_active = true",
                "expected_tables": ["patient_tracker"],
                "expected_filters": ["is_active"],
                "expected_aggregations": ["COUNT"],
                "category": "count",
                "difficulty": "easy"
            }
        ]
        metrics = self.evaluator.evaluate_batch(entries)
        assert metrics["total_queries"] == 1
        assert metrics["avg_overall_score"] > 0.9


# =============================================================================
# Reflection Service Tests
# =============================================================================

class TestReflectionServiceEnhancements:
    """Tests for the enhanced reflection service."""
    
    def setup_method(self):
        from backend.services.reflection_service import SQLCritiqueService
        self.service = SQLCritiqueService(schema_graph=None)
    
    def test_extract_tables(self):
        """Test table extraction."""
        tables = self.service._extract_tables_from_sql(
            "SELECT * FROM patient_tracker JOIN site ON patient_tracker.site_id = site.id"
        )
        assert "patient_tracker" in tables
        assert "site" in tables
    
    def test_safe_select(self):
        """Test safe SELECT detection."""
        assert self.service._is_safe_select_query("SELECT COUNT(*) FROM t") is True
        assert self.service._is_safe_select_query("DROP TABLE t") is False
        assert self.service._is_safe_select_query("DELETE FROM t") is False
    
    def test_validate_aggregation_missing_group_by(self):
        """Test aggregation validation catches missing GROUP BY."""
        issues = self.service._validate_aggregation(
            "SELECT name, COUNT(*) FROM patient_tracker"
        )
        assert len(issues) > 0
        assert "GROUP BY" in issues[0]
    
    def test_validate_aggregation_with_group_by(self):
        """Test aggregation validation passes with GROUP BY."""
        issues = self.service._validate_aggregation(
            "SELECT name, COUNT(*) FROM patient_tracker GROUP BY name"
        )
        assert len(issues) == 0
    
    def test_validate_aggregation_count_star_only(self):
        """Test pure COUNT(*) without GROUP BY is fine."""
        issues = self.service._validate_aggregation(
            "SELECT COUNT(*) FROM patient_tracker WHERE is_active = true"
        )
        assert len(issues) == 0
    
    def test_quick_validate_known_tables(self):
        """Test quick validation passes for known tables."""
        from backend.models.schemas import CritiqueResponse
        result = self.service._quick_validate(
            "SELECT COUNT(*) FROM patient_tracker WHERE is_active = true",
            "patient_tracker patient_visit site"
        )
        assert result is not None
        assert result.is_valid is True
    
    def test_quick_validate_patient_table_rejection(self):
        """Test that bare 'patient' table is rejected when patient_tracker exists in schema."""
        result = self.service._quick_validate(
            "SELECT * FROM patient",
            "patient_tracker patient"
        )
        assert result is not None
        assert result.is_valid is False
        assert "patient_tracker" in result.issues[0]

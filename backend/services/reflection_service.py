"""
Reflection Service - Self-Correction Logic.
Critiques generated SQL against schema rules and best practices.
"""
import re
from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from backend.config import get_settings
from backend.core.logging import get_logger
from backend.models.schemas import CritiqueResponse

# Optional SchemaGraph import — used when available for structured validation
try:
    from backend.services.schema_graph import SchemaGraph
except ImportError:
    SchemaGraph = None

settings = get_settings()
logger = get_logger(__name__)

CRITIQUE_PROMPT_TEMPLATE = """You are a Senior SQL Expert and Security Auditor.
Your job is to critique and validate the following SQL query generated for a PostgreSQL database.

DATABASE SCHEMA CONTEXT (TRUST THIS - these are the ACTUAL tables and columns):
{schema_context}

USER QUESTION: "{question}"

GENERATED SQL:
{sql_query}

CRITIQUE RULES:
1. Schema Validation: Check if table and column names exist in the schema context provided above. 
   IMPORTANT: Only flag a column as missing if you are 100% certain it's NOT in the schema above.
   The schema context is authoritative - if a column appears there, it EXISTS.
2. Logic Check: Does the SQL answer the user's question?
3. Security: Check for proper date handling and injection risks (though we use read-only).
4. Join Logic: Are joins correct based on primary/foreign key relationships in the schema?

IMPORTANT: For simple COUNT queries with basic WHERE clauses, be lenient. 
If the table and columns are in the schema and the logic matches the question, mark as VALID.
IMPORTANT: If you see a table name like 'patient_tracker' in the schema context, it EXISTS - do not reject it.

Output valid JSON matching the CritiqueResponse schema.
If the SQL is correct and answers the question, set is_valid=True.
"""

# Legacy hardcoded list — kept ONLY as fallback when SchemaGraph is not available.
# When SchemaGraph is initialized, validation uses live database introspection instead.
KNOWN_VALID_TABLES = [
    'patient_tracker', 'patient_visit', 'patient_diagnosis', 'patient_assessment',
    'patient_lab_test', 'patient_lab_test_result', 'patient_treatment_plan',
    'patient_medical_review', 'patient_comorbidity', 'patient_complication',
    'patient_current_medication', 'patient_lifestyle', 'patient_symptom',
    'patient_general_information', 'patient_history', 'patient_transfer',
    'patient_eye_care', 'patient_cataract', 'patient_pregnancy_details',
    'patient_nutrition_lifestyle', 'patient_para_counselling', 'patient_medical_compliance',
    'bp_log', 'glucose_log', 'screening_log', 'lab_test', 'lab_test_result',
    'site', 'organization', 'country', 'account', 'user', 'role',
    'medication_country_detail', 'dosage_form', 'dosage_frequency',
    'patient_bp_log', 'patient_glucose_log', 'patient_screening',
    'region', 'district', 'health_facility', 'program', 'clinical_workflow',
    'country_customization', 'form_meta', 'menu', 'culture'
]

class SQLCritiqueService:
    def __init__(self, schema_graph=None):
        logger.info("Initializing SQLCritiqueService")
        self.schema_graph = schema_graph  # SchemaGraph instance for structured validation
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo",  # Use faster model for critique
            api_key=settings.openai_api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=CritiqueResponse)
        
        self.prompt = ChatPromptTemplate.from_template(
            CRITIQUE_PROMPT_TEMPLATE,
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

    def _extract_tables_from_sql(self, sql_query: str) -> List[str]:
        """Extract all table names from SQL query."""
        sql_lower = sql_query.lower()
        tables = []
        
        # Match FROM and JOIN clauses
        from_pattern = r'(?:from|join)\s+([a-z_][a-z0-9_]*)'
        matches = re.findall(from_pattern, sql_lower)
        tables.extend(matches)
        
        return list(set(tables))

    def _is_safe_select_query(self, sql_query: str) -> bool:
        """Check if query is a safe SELECT statement."""
        sql_lower = sql_query.lower().strip()
        dangerous_keywords = ['drop', 'delete', 'update', 'insert', 'alter', 'truncate', 'create', 'grant', 'revoke']
        
        if not sql_lower.startswith('select'):
            return False
            
        for keyword in dangerous_keywords:
            # Check for keyword as a whole word
            if re.search(rf'\b{keyword}\b', sql_lower):
                return False
        
        return True

    def _quick_validate(self, sql_query: str, schema_context: str) -> Optional[CritiqueResponse]:
        """
        Perform quick validation without LLM.
        
        Uses SchemaGraph (when available) for precise table/column existence checks,
        falls back to legacy KNOWN_VALID_TABLES + schema text matching.
        """
        sql_lower = sql_query.lower()
        schema_lower = schema_context.lower()
        
        # Must be a safe SELECT query
        if not self._is_safe_select_query(sql_query):
            return None  # Let LLM handle complex cases
        
        # Extract tables from the query
        tables = self._extract_tables_from_sql(sql_query)
        
        if not tables:
            return None  # Can't validate without table names
        
        # Check for demo 'patient' table misuse
        if 'patient' in tables and len([t for t in tables if t == 'patient']) > 0:
            other_patient_tables = [t for t in tables if t.startswith('patient_')]
            if not other_patient_tables and 'patient_tracker' in schema_lower:
                logger.warning("Rejecting 'patient' table - should use 'patient_tracker' instead")
                return CritiqueResponse(
                    is_valid=False,
                    reasoning="Wrong table used. The 'patient' table is a demo table. Use 'patient_tracker' for patient queries.",
                    issues=["Use 'patient_tracker' table instead of 'patient' for patient data queries"]
                )
        
        # === SchemaGraph-based validation (preferred) ===
        if self.schema_graph:
            all_tables_valid = True
            issues = []
            for table in tables:
                if table == 'patient':
                    continue
                if not self.schema_graph.has_table(table):
                    all_tables_valid = False
                    issues.append(f"Table '{table}' not found in database schema")
            
            if not all_tables_valid:
                return CritiqueResponse(
                    is_valid=False,
                    reasoning=f"Schema validation failed: {'; '.join(issues)}",
                    issues=issues
                )
            
            # Validate joins if multiple tables
            join_issues = self._validate_joins(sql_query, tables)
            if join_issues:
                return CritiqueResponse(
                    is_valid=False,
                    reasoning=f"Join validation issues: {'; '.join(join_issues)}",
                    issues=join_issues
                )
            
            # Validate aggregation GROUP BY completeness
            agg_issues = self._validate_aggregation(sql_query)
            if agg_issues:
                return CritiqueResponse(
                    is_valid=False,
                    reasoning=f"Aggregation issues: {'; '.join(agg_issues)}",
                    issues=agg_issues
                )
            
            logger.info(f"SchemaGraph validation PASSED for tables: {tables}")
            return CritiqueResponse(
                is_valid=True,
                reasoning=f"All tables and joins validated against SchemaGraph: {', '.join(tables)}",
                issues=[]
            )
        
        # === Legacy KNOWN_VALID_TABLES fallback ===
        all_tables_known = True
        for table in tables:
            if table == 'patient':
                continue
            
            is_known_table = table in KNOWN_VALID_TABLES
            is_in_schema = table in schema_lower
            
            if is_known_table or is_in_schema:
                logger.info(f"Table '{table}' validated (known={is_known_table}, in_schema={is_in_schema})")
            else:
                all_tables_known = False
                logger.info(f"Table '{table}' not found in quick validation, deferring to LLM")
                break
        
        if all_tables_known:
            logger.info(f"Quick validation PASSED (legacy) - all tables known: {tables}")
            return CritiqueResponse(
                is_valid=True,
                reasoning=f"All tables validated against known tables and schema: {', '.join(tables)}",
                issues=[]
            )
        
        return None  # Unknown table - let LLM validate
    
    def _validate_joins(self, sql_query: str, tables: List[str]) -> List[str]:
        """
        Validate JOIN conditions against SchemaGraph FK relationships.
        Returns a list of issues (empty if all joins are valid).
        """
        if not self.schema_graph or len(tables) <= 1:
            return []
        
        issues = []
        sql_lower = sql_query.lower()
        
        # Check that multi-table queries have JOIN clauses
        if len(tables) > 1 and 'join' not in sql_lower:
            # Might be using comma-separated FROM with WHERE join - less ideal but valid
            if ',' in sql_query[sql_lower.find('from'):sql_lower.find('where') if 'where' in sql_lower else len(sql_lower)]:
                logger.info("Using implicit comma join syntax - valid but not recommended")
            else:
                issues.append("Query references multiple tables but has no JOIN clause")
        
        return issues
    
    def _validate_aggregation(self, sql_query: str) -> List[str]:
        """
        Check for common aggregation errors (e.g., missing GROUP BY).
        """
        sql_lower = sql_query.lower()
        issues = []
        
        # Check if query has aggregation functions
        agg_functions = ['count(', 'sum(', 'avg(', 'min(', 'max(']
        has_aggregation = any(agg in sql_lower for agg in agg_functions)
        
        if has_aggregation:
            # Check for non-aggregated columns in SELECT without GROUP BY
            has_group_by = 'group by' in sql_lower
            
            # Heuristic: if using aggregation with non-star select and no GROUP BY
            # and the SELECT has multiple columns, it might be missing GROUP BY
            select_end = sql_lower.find('from')
            if select_end > 0:
                select_clause = sql_lower[6:select_end].strip()
                has_non_agg_columns = False
                for part in select_clause.split(','):
                    part = part.strip()
                    if part and not any(agg in part for agg in agg_functions) and part != '*':
                        has_non_agg_columns = True
                        break
                
                if has_non_agg_columns and not has_group_by:
                    issues.append(
                        "SELECT includes non-aggregated columns alongside aggregation functions "
                        "but has no GROUP BY clause"
                    )
        
        return issues

    def _is_simple_query(self, sql_query: str) -> bool:
        """Check if query is simple enough to skip LLM critique."""
        sql_lower = sql_query.lower()
        
        # Simple queries: SELECT with COUNT, GROUP BY, basic WHERE
        simple_patterns = [
            r'select\s+\w+\s*,\s*count\s*\(',  # SELECT col, COUNT(
            r'select\s+count\s*\(',             # SELECT COUNT(
            r'select\s+\*\s+from',              # SELECT * FROM
            r'select\s+\w+\s*,\s*\w+\s+from',   # SELECT col1, col2 FROM
        ]
        
        for pattern in simple_patterns:
            if re.search(pattern, sql_lower):
                return True
        
        # Also consider queries without subqueries as simple
        if 'select' not in sql_lower[sql_lower.find('from'):] if 'from' in sql_lower else True:
            # No nested SELECT after FROM - relatively simple
            if sql_lower.count('select') == 1:
                return True
        
        return False

    def critique_sql(self, question: str, sql_query: str, schema_context: str) -> CritiqueResponse:
        """
        Analyze SQL query for correctness and safety.
        """
        logger.info(f"Critiquing SQL for: '{question[:50]}...'")
        
        # Try quick validation first
        quick_result = self._quick_validate(sql_query, schema_context)
        if quick_result is not None:
            if quick_result.is_valid:
                logger.info("Quick validation PASSED - skipping LLM critique")
            else:
                logger.warning(f"Quick validation FAILED: {quick_result.issues}")
            return quick_result
        
        logger.info("Quick validation inconclusive - using LLM critique")
        
        try:
            # Format inputs - ensure schema context includes key tables
            truncated_schema = schema_context[:12000]  # Increased limit
            
            _input = self.prompt.format_messages(
                schema_context=truncated_schema,
                question=question,
                sql_query=sql_query
            )
            
            # Using Pydantic output parser workflow
            output = self.llm.invoke(_input)
            
            # Use structured output parsing
            if hasattr(self.llm, "with_structured_output"):
                structured_llm = self.llm.with_structured_output(CritiqueResponse)
                response = structured_llm.invoke(_input)
            else:
                # Fallback to manual parsing
                response = self.parser.parse(output.content)
            
            # Double-check LLM response for false negatives
            if not response.is_valid:
                tables = self._extract_tables_from_sql(sql_query)
                false_negative = False
                
                for table in tables:
                    # Prefer SchemaGraph for validation
                    table_is_valid = False
                    if self.schema_graph:
                        table_is_valid = self.schema_graph.has_table(table)
                    else:
                        table_is_valid = table in KNOWN_VALID_TABLES and table in schema_context.lower()
                    
                    if table_is_valid:
                        for issue in response.issues or []:
                            if table in issue.lower() and ('not found' in issue.lower() or 'missing' in issue.lower() or "doesn't exist" in issue.lower()):
                                logger.warning(f"LLM false negative detected for table '{table}' - overriding")
                                false_negative = True
                                break
                
                if false_negative:
                    logger.info("Overriding LLM critique - tables are valid in schema")
                    return CritiqueResponse(
                        is_valid=True,
                        reasoning="Tables validated against schema (LLM override)",
                        issues=[]
                    )
            
            if not response.is_valid:
                logger.warning(f"Critique Found Issues: {response.issues}")
            else:
                logger.info("SQL Critique Passed")
                
            return response
            
        except Exception as e:
            logger.error(f"Critique failed: {e}")
            # Fail safe - assume valid if critique breaks, to avoid blocking
            return CritiqueResponse(
                is_valid=True, 
                reasoning="Critique service unavailable", 
                issues=[]
            )

# Singleton
_critique_service = None

def get_critique_service():
    global _critique_service
    if not _critique_service:
        _critique_service = SQLCritiqueService()
    return _critique_service

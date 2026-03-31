import json
import time
from typing import Optional, Dict, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from backend.config import get_settings, get_llm_settings
from backend.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# =============================================================================
# Intent Classification Cache (Task 6)
# =============================================================================
# Caches LLM classification results to avoid redundant API calls.
# Queries often repeat within a session (follow-up questions, retries).
_CLASSIFICATION_CACHE: Dict[str, Tuple['IntentClassification', float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes
_CACHE_MAX_SIZE = 200


class IntentClassification(BaseModel):
    """Structured output for the intent routing decision."""
    intent: str = Field(
        description="The classified intent: 'A' for SQL only, 'B' for Vector only, or 'C' for Hybrid."
    )
    sql_filter: Optional[str] = Field(
        description="For Intent C ONLY, a PostgreSQL query to extract the relevant IDs (e.g., patient_id). Return None for Intent A or B.",
        default=None
    )
    confidence_score: float = Field(
        description="Confidence score for the selected intent, between 0.0 and 1.0.",
        default=1.0
    )


class IntentClassifier:
    """
    Intent Router for clinical Hybrid RAG system.
    Routes queries to SQL Engine, Vector Engine, or Hybrid approach.
    """
    
    def __init__(self, llm=None):
        if llm:
            self.llm = llm
        else:
            # Get LLM settings from database (runtime configurable)
            llm_settings = get_llm_settings()
            self.llm = ChatOpenAI(
                temperature=0,
                model_name=llm_settings.get('model_name', 'gpt-4o'),
                api_key=settings.openai_api_key
            )
        
        self.structured_llm = self.llm.with_structured_output(IntentClassification)
        
        import os
        try:
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "agent_spec", "prompt_templates", "intent_router.md")
            with open(template_path, "r") as f:
                system_prompt = f.read()
        except Exception:
            system_prompt = "You are Antigravity, the Intent Router. Route queries to SQL or Vector."

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Query: {query}\n\nSchema Context (if needed for Intent C):\n{schema}")
        ])

    def classify(self, query: str, schema_context: str = "") -> IntentClassification:
        """Classify the user intent and optionally generate a SQL filter."""
        logger.info(f"Classifying intent for query: {query}")
        
        # Task 6: Check classification cache first
        cache_key = query.strip().lower()
        now = time.time()
        if cache_key in _CLASSIFICATION_CACHE:
            cached_result, timestamp = _CLASSIFICATION_CACHE[cache_key]
            if now - timestamp < _CACHE_TTL_SECONDS:
                logger.info(f"Classification cache HIT: Intent={cached_result.intent}")
                return cached_result
            else:
                del _CLASSIFICATION_CACHE[cache_key]  # Expired
        
        # Quick heuristic pre-check for obvious SQL queries
        query_lower = query.lower()
        sql_keywords = [
            'count', 'total', 'how many', 'average', 'rate', 'percentage', 'percent',
            'breakdown', 'distribution', 'by age', 'by gender', 'by region', 'by district',
            'highest', 'lowest', 'top', 'bottom', 'rank', 'trend', 'monthly', 'yearly',
            'cascade', 'funnel', 'screened', 'diagnosed', 'treated', 'controlled',
            'male', 'female', 'coverage', 'screening', 'vs target'
        ]
        
        if any(keyword in query_lower for keyword in sql_keywords):
            logger.info(f"Pre-classified as Intent A (SQL) based on keywords")
            result = IntentClassification(intent="A", sql_filter=None, confidence_score=1.0)
            _CLASSIFICATION_CACHE[cache_key] = (result, now)
            return result
        
        # Task 6: Quick heuristic for obvious Vector-only queries
        vector_keywords = [
            'notes', 'documents', 'clinical summaries', 'tell me about',
            'find mentions', 'patient history', 'narrative', 'what did',
            'doctor wrote', 'patient notes', 'document search', 'records for patient',
            'medical history', 'patient summary'
        ]
        
        if any(keyword in query_lower for keyword in vector_keywords):
            logger.info(f"Pre-classified as Intent B (Vector) based on keywords")
            result = IntentClassification(intent="B", sql_filter=None, confidence_score=1.0)
            _CLASSIFICATION_CACHE[cache_key] = (result, now)
            return result
        
        try:
            chain = self.prompt | self.structured_llm
            result = chain.invoke({"query": query, "schema": schema_context})
            logger.info(f"Classification result: Intent={result.intent}, SQL Filter={result.sql_filter}, Confidence={result.confidence_score}")
            
            # Cache the LLM result
            _CLASSIFICATION_CACHE[cache_key] = (result, now)
            # Evict oldest if over capacity
            if len(_CLASSIFICATION_CACHE) > _CACHE_MAX_SIZE:
                oldest_key = next(iter(_CLASSIFICATION_CACHE))
                del _CLASSIFICATION_CACHE[oldest_key]
            
            return result
        except Exception as e:
            logger.error(f"Failed to classify intent: {e}")
            # Fallback to SQL for most analytical queries with low confidence
            return IntentClassification(intent="A", sql_filter=None, confidence_score=0.5)

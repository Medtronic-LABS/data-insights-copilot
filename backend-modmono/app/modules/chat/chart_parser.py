"""
Chart data parser for extracting visualization data from LLM responses.

Parses JSON blocks from LLM outputs to generate chart configurations
compatible with the frontend ChartRenderer component.
"""
import re
import json
from typing import Optional, Tuple, List, Dict, Any

from app.core.utils.logging import get_logger
from app.modules.chat.schemas import ChartData

logger = get_logger(__name__)


def parse_chart_data(response: str) -> Tuple[Optional[ChartData], str]:
    """
    Parse chart data from an LLM response.
    
    Extracts JSON blocks containing chart configurations and returns
    a ChartData object along with the cleaned response text.
    
    Args:
        response: The full LLM response text
        
    Returns:
        Tuple of (ChartData or None, cleaned response text)
    """
    chart_data = None
    cleaned_response = response
    
    # Try to extract JSON block - handle nested braces properly
    # Look for ```json ... ``` block
    json_match = re.search(r'''```json\s*([\s\S]*?)\s*```''', response)
    
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            data = json.loads(json_str)
            
            # Extract chart data - handle both wrapped and direct formats
            chart_json = None
            if "chart_json" in data:
                chart_json = data["chart_json"]
            elif "type" in data and ("data" in data or "value" in data):
                # LLM returned the chart object directly
                chart_json = data
            
            if chart_json:
                chart_data = _validate_and_create_chart(chart_json)
                
                if chart_data:
                    logger.info(f"Successfully parsed chart data: {chart_data.title or 'Untitled'}")
                    
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse chart JSON: {e}")
            logger.debug(f"JSON string was: {json_str[:200]}...")
        except Exception as e:
            logger.warning(f"Failed to create ChartData: {e}")
    
    # Clean the response by removing JSON blocks
    cleaned_response = clean_response_text(response)
    
    return chart_data, cleaned_response


def _validate_and_create_chart(chart_json: Dict[str, Any]) -> Optional[ChartData]:
    """
    Validate chart JSON and create a ChartData object.
    
    Handles compatibility fixes and auto-generation of missing fields.
    """
    try:
        # Compatibility fix for Chart.js style output (datasets) -> Frontend style (values)
        if "data" in chart_json and isinstance(chart_json["data"], dict):
            cdata = chart_json["data"]
            if "datasets" in cdata and "values" not in cdata:
                # Extract data from first dataset
                try:
                    datasets = cdata["datasets"]
                    if datasets and isinstance(datasets, list):
                        cdata["values"] = datasets[0].get("data", [])
                        logger.info("Transformed Chart.js style 'datasets' to 'values'")
                except Exception as e:
                    logger.warning(f"Failed to transform chart datasets: {e}")
        
        # Auto-generate title if missing
        if "title" not in chart_json or not chart_json["title"]:
            chart_type = chart_json.get("type", "Chart")
            chart_json["title"] = f"{chart_type.capitalize()} Visualization"
            logger.info(f"Auto-generated missing chart title: {chart_json['title']}")
        
        # Validate required fields
        if "type" not in chart_json:
            logger.warning("Chart JSON missing required 'type' field")
            return None
        
        # Create ChartData object
        return ChartData(**chart_json)
        
    except Exception as e:
        logger.warning(f"Validation failed for chart data: {e}")
        return None


def clean_response_text(response: str) -> str:
    """
    Remove JSON code blocks from response text.
    
    Args:
        response: The full response text
        
    Returns:
        Cleaned text with JSON blocks removed
    """
    # Remove JSON code blocks - use [\s\S]*? to match across newlines
    cleaned = re.sub(r'''```json\s*[\s\S]*?\s*```''', '', response)
    return cleaned.strip()

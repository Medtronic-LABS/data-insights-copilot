# Result Formatter Prompt

Convert SQL query results into clear, natural language answers with optional chart visualization.

## Input Context
Question: {question}
SQL Query: {sql}
Execution Time: {execution_time_ms}ms
Total Rows: {total_rows}

## Results Data
{results}

## Instructions
1. First, provide a concise natural language answer explaining the data
2. Highlight key insights, trends, or notable values
3. If data is suitable for visualization, append a chart JSON specification

## Chart Type Selection Guide
- **funnel**: Care cascade, patient journey, sequential stages
- **bullet**: Actual vs target comparisons, performance metrics
- **horizontal_bar**: Rankings (top/bottom N, highest/lowest)
- **treemap**: Regional/hierarchical distributions
- **line**: Time series trends (monthly, yearly)
- **bar**: Categorical breakdowns (by age, gender, type)
- **pie**: Proportions and percentage distributions
- **gauge**: Single rate/percentage values with thresholds
- **scorecard**: Single numeric values

## Chart JSON Format
```json
{
    "chart_json": {
        "title": "Descriptive Chart Title",
        "type": "<chart_type>",
        "data": {
            "labels": ["label1", "label2", ...],
            "values": [value1, value2, ...]
        }
    }
}
```

## Response Format
Provide the natural language answer first, then append the chart JSON in a code block if visualization is appropriate.

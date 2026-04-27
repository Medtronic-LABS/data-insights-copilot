# SQL Fix Hints by Error Type

Error-type specific hints for SQL correction. Use the appropriate section based on the error classification.

## COLUMN_NOT_FOUND
- Check column names against the schema (they may have different casing or underscores)
- The column might be in a different table - check all available tables
- Use table aliases consistently when joining

## TABLE_NOT_FOUND
- Check table names against the schema exactly
- Table names are case-sensitive in some databases
- Ensure you're using the correct schema/database prefix

## WINDOW_FUNCTION_MISUSE
CRITICAL FIX FOR WINDOW FUNCTIONS:
- Window functions (LAG, LEAD, ROW_NUMBER, RANK) CANNOT be in WHERE clause
- Window functions CANNOT be in GROUP BY clause
- ALWAYS use CTE pattern:
```sql
WITH computed AS (
    SELECT *, ROW_NUMBER() OVER (...) AS rn
    FROM table
)
SELECT * FROM computed WHERE rn = 1
```

## AGGREGATE_MISUSE
- Aggregates (COUNT, SUM, AVG) CANNOT be in WHERE clause - use HAVING
- All non-aggregated columns in SELECT must be in GROUP BY
- Use subquery/CTE for filtering on aggregate results

## TYPE_MISMATCH
- Check column types in schema and cast appropriately
- For date comparisons, ensure both sides are DATE/TIMESTAMP
- Use CAST(column AS TYPE) or ::type syntax

## DATE_FUNCTION_ERROR
DuckDB DATE RULES:
- DATEDIFF requires 3 arguments: DATEDIFF('day', start_date, end_date)
- Date subtraction: date_col - INTERVAL '90 days'
- Use CAST(varchar_col AS TIMESTAMP) for string dates
- DATE_TRUNC('month', date_col) for truncation

## AMBIGUOUS_COLUMN
- Use table aliases for all column references
- Example: t.column_name instead of just column_name
- Prefix with table alias in JOIN conditions

## SYNTAX_ERROR
- Check for missing commas, parentheses, or quotes
- Ensure keywords are spelled correctly
- Check that string literals use single quotes

## DIVISION_BY_ZERO
- Wrap denominator with NULLIF(denominator, 0)
- Use CASE WHEN denominator = 0 THEN NULL ELSE numerator/denominator END

## DEFAULT
- Review the error message and fix accordingly
- Check schema for correct table and column names
- Verify SQL syntax matches the target dialect

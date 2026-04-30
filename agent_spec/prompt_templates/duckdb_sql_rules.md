CRITICAL DUCKDB SQL RULES:
1. Window functions (LAG, LEAD, ROW_NUMBER, RANK, DENSE_RANK, FIRST_VALUE, LAST_VALUE) CANNOT be used in WHERE clause - use CTE pattern instead
2. Window functions CANNOT be used in GROUP BY clause - use CTE pattern instead
3. Aggregate functions (COUNT, SUM, AVG, MIN, MAX) CANNOT be used in WHERE clause - use subquery or CTE with HAVING
4. Date difference: Use (date1 - date2) for interval or DATEDIFF('day', start_date, end_date) with 3 arguments
5. For first/last value comparisons, ALWAYS use ROW_NUMBER() in a CTE, then filter in outer query
6. Use DATE_TRUNC('month', date_col) for date truncation, not MONTH() or DATEPART()
7. Use INTERVAL '90 days' syntax for date arithmetic, not DATE_SUB() or DATEADD()
8. For consecutive streak detection, use the ROW_NUMBER difference technique in CTEs
9. String concatenation uses || operator, not CONCAT() in some contexts
10. Boolean values are TRUE/FALSE, not 1/0
11. **TYPE CASTING FOR DATE COLUMNS**: If a date column is VARCHAR type (check schema), CAST it before date comparisons:
    - Use CAST(column_name AS TIMESTAMP) or column_name::TIMESTAMP
    - Example: WHERE CAST(created_at AS TIMESTAMP) >= CURRENT_DATE - INTERVAL '1 year'
    - Also cast before DATE_TRUNC: DATE_TRUNC('month', CAST(created_at AS TIMESTAMP))
12. **CHECK COLUMN TYPES IN SCHEMA**: Before date/numeric operations, verify the column type. If VARCHAR contains dates, cast explicitly.
13. **GREATEST/LEAST FOR ROW-WISE MIN/MAX**: To find min/max ACROSS COLUMNS in a single row, use GREATEST() and LEAST(), NOT max() or min():
    - WRONG: max(col1, col2, col3) or min(col1, col2, col3) - These are AGGREGATE functions!
    - CORRECT: GREATEST(col1, col2, col3) or LEAST(col1, col2, col3)
    - Example: SELECT GREATEST(pulse_1, pulse_2, COALESCE(pulse_3, 0)) - LEAST(pulse_1, pulse_2, COALESCE(pulse_3, 0)) AS pulse_variance
14. **COALESCE FOR NULL HANDLING**: Use COALESCE(column, default_value) to handle NULLs in calculations.
15. **AGGREGATE vs ROW-WISE FUNCTIONS**: 
    - max()/min() are AGGREGATE functions - they work ACROSS ROWS (vertical)
    - GREATEST()/LEAST() are SCALAR functions - they work ACROSS COLUMNS in a single row (horizontal)
16. **TIMEZONE-AWARE TIMESTAMPS & DIRTY STRINGS**: If a timestamp column contains timezone info (e.g., "+0300", "UTC", "Z") or if a VARCHAR needs conversion, ALWAYS use TIMESTAMPTZ:
    - WRONG: CAST(created_at AS TIMESTAMP) - fails if string has timezone or is already a DATE.
    - CORRECT: CAST(created_at AS TIMESTAMPTZ) or created_at::TIMESTAMPTZ
    - Example: DATE_TRUNC('month', CAST(created_at AS TIMESTAMPTZ))
    - For any string-to-date conversion where formatting is complex, prefer TIMESTAMPTZ.
17. **PREFER DEDICATED DATE COLUMNS**: If a table has both a date column (like 'ymd', 'date') and a timestamp, prefer the dedicated date column to avoid timezone issues.
18. **NO SUBSTRING FOR DATES**: Never use SUBSTRING() on a DATE or TIMESTAMP column. Only use it on VARCHAR if absolutely necessary. DuckDB's CAST is usually smart enough without it.
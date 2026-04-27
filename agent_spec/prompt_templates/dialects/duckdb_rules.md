# DuckDB Dialect Rules (Extended)

## CRITICAL DUCKDB SQL RULES - MUST FOLLOW

### 1. Window Functions in WHERE/GROUP BY - USE CTE PATTERN
Window functions (LAG, LEAD, ROW_NUMBER, RANK, etc.) CANNOT be used in WHERE or GROUP BY clauses.

**WRONG:**
```sql
WHERE LAG(col) OVER (...) IS NOT NULL
GROUP BY SUM(CASE WHEN LAG(col) OVER (...) ...)
```

**CORRECT:**
```sql
WITH computed AS (
    SELECT *, LAG(col) OVER (...) AS prev_col
    FROM table
)
SELECT * FROM computed WHERE prev_col IS NOT NULL
```

### 2. Aggregates in WHERE - USE SUBQUERY/CTE
Aggregate functions (AVG, STDDEV, COUNT, SUM) CANNOT be used in WHERE clause.

**WRONG:**
```sql
WHERE col > AVG(col) OR WHERE STDDEV(col) > 0
```

**CORRECT:**
```sql
WITH stats AS (SELECT AVG(col) AS avg_val FROM table)
SELECT * FROM table, stats WHERE col > stats.avg_val
```

### 3. Date Difference - THREE ARGUMENTS REQUIRED
**WRONG:** `DATEDIFF(date1, date2)`
**CORRECT:** `DATEDIFF('day', date1, date2)` or `CAST(date2 AS DATE) - CAST(date1 AS DATE)`

### 4. Date Subtraction
**WRONG:** `DATE_SUB(date, INTERVAL 90 DAY)`
**CORRECT:** `CAST(date AS DATE) - INTERVAL '90 days'`

### 5. First/Last Value Comparison - ALWAYS USE CTE
```sql
WITH ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY id ORDER BY date ASC) AS first_rank,
        ROW_NUMBER() OVER (PARTITION BY id ORDER BY date DESC) AS last_rank
    FROM table
)
SELECT f.*, l.col AS last_col
FROM ranked f
JOIN ranked l ON f.id = l.id
WHERE f.first_rank = 1 AND l.last_rank = 1
```

### 6. Consecutive Streak Detection - USE ROW_NUMBER DIFFERENCE
```sql
WITH ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY id ORDER BY date) -
        ROW_NUMBER() OVER (PARTITION BY id, category ORDER BY date) AS streak_group
    FROM table
)
SELECT id, category, COUNT(*) AS streak_length
FROM ranked
GROUP BY id, category, streak_group
```

### 7. String Comparisons
- Use `ILIKE` for case-insensitive string comparisons
- Use `LIKE` for case-sensitive comparisons

### 8. Boolean Values
- Boolean columns may be stored as strings
- Use `= 'true'` or `= 'false'` for string booleans
- Use `= TRUE` or `= FALSE` for native booleans

### 9. Timestamps with Offsets
DuckDB may fail on timestamps with explicit timezone offsets (e.g., '+0000', '+0300').

**WRONG:** `CAST(created_at AS TIMESTAMP)` -- fails if created_at has '+0300'
**CORRECT:** `TRY_CAST(SUBSTRING(CAST(created_at AS VARCHAR), 1, 19) AS TIMESTAMP)`

### 10. Additional Rules
- Use `DATE_TRUNC('month', date_col)` for date truncation
- Use `GREATEST/LEAST` for row-wise min/max across columns (NOT aggregate min/max)
- Boolean values are `TRUE/FALSE`, not `1/0`

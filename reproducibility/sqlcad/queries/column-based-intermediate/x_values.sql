WITH x_values AS (
    SELECT DISTINCT -a0/a1 AS value
    FROM {start_table}
    WHERE a1 <> 0
),
-- Intervals + sample points in one go.
sample_points AS (
    SELECT
        value AS sample_point
    FROM x_values

    UNION

    SELECT sample_point
    FROM (
        SELECT
            -- LEAD is way faster than a self join + GROUP BY + MIN().
            (a.value + LEAD(a.value) OVER (ORDER BY a.value)) / 2 AS sample_point
        FROM x_values a
    )
    WHERE sample_point IS NOT NULL

    UNION

    -- Artifical lower and upper interval.
    -- The coalesce ensures we have a sample value for when there are no
    -- x_values, so the interval would be -inf,+inf, so sample point 0.
    SELECT COALESCE(MIN(value) - 1, 0) FROM x_values
    UNION
    SELECT COALESCE(MAX(value) + 1, 0) FROM x_values
)
SELECT
    ROW_NUMBER() OVER (ORDER BY sample_point) AS id,
    sample_point
FROM sample_points
ORDER BY sample_point;

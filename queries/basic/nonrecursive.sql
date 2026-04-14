WITH
constraints_involving_z_coeffs AS (
    SELECT *
    FROM Coefficient
    -- Hardcoded for now; will have to fetch dynamically for recursive variant.
    WHERE dimension = 3
        AND value <> 0
),
zprojection_normalized_constraints AS (
    SELECT
        c.constraint_id,
        c.dimension,
        -- This normalizes the coefficients (e.g. when projecting z away,
        -- divides everything by the value of the coefficient of z)
        c.value / zc.value AS value
    FROM Coefficient c
    JOIN constraints_involving_z_coeffs zc
        ON c.constraint_id = zc.constraint_id
        AND  c.dimension < zc.dimension
),
zprojection_intersect_coeffs AS (
    SELECT
        (nc1.constraint_id || 'x' || nc2.constraint_id) AS constraint_id,
        nc1.dimension,
        nc2.value - nc1.value AS value
    FROM zprojection_normalized_constraints nc1
    JOIN zprojection_normalized_constraints nc2
        ON nc1.constraint_id <> nc2.constraint_id
        AND nc1.constraint_id < nc2.constraint_id -- Unique pairs (i.e. only 1x3, not also 3x1)
        AND nc1.dimension = nc2.dimension
),
-- Finally, we arrive at our xy projections.
xy_projections AS (
    -- Constraints from lower dimensions
    SELECT * FROM Coefficient
    WHERE constraint_id NOT IN
        (SELECT constraint_id FROM constraints_involving_z_coeffs)
    UNION ALL
    -- Combined with the intersections we just calculated, but filter out
    -- impossible constraints (e.g. 2 +0x + 0y=0).
    SELECT * FROM zprojection_intersect_coeffs zc1
    WHERE EXISTS (
        SELECT 1
        FROM zprojection_intersect_coeffs zc2
        WHERE zc1.constraint_id = zc2.constraint_id
        AND zc2.dimension > 0
        AND zc2.value <> 0
    )
),
-- Now onto projecting y away
constraints_involving_y_coeffs AS (
    SELECT *
    FROM xy_projections
    WHERE dimension = 2
        AND value <> 0
),
xy_normalized_constraints AS (
    SELECT
        c.constraint_id,
        c.dimension,
        c.value / yc.value AS value
    FROM xy_projections c
    JOIN constraints_involving_y_coeffs yc
        ON c.constraint_id = yc.constraint_id
        AND  c.dimension < yc.dimension
),
xy_intersect_coeffs AS (
    SELECT
        (nc1.constraint_id || 'x' || nc2.constraint_id) AS constraint_id,
        nc1.dimension,
        nc2.value - nc1.value AS value
    FROM xy_normalized_constraints nc1
    JOIN xy_normalized_constraints nc2
        ON nc1.constraint_id <> nc2.constraint_id
        AND nc1.constraint_id < nc2.constraint_id
        AND nc1.dimension = nc2.dimension
),
x_projections AS (
    SELECT * FROM xy_projections
    WHERE constraint_id NOT IN
        (SELECT constraint_id FROM constraints_involving_y_coeffs)
    UNION ALL
    SELECT * FROM xy_intersect_coeffs c1
    WHERE EXISTS (
        SELECT 1
        FROM xy_intersect_coeffs c2
        WHERE c1.constraint_id = c2.constraint_id
        AND c2.dimension > 0
        AND c2.value <> 0
    )
),
-- We are done with projecting down; now we calculate the x-intervals.
x_values AS (
    SELECT DISTINCT -coeff0.value / coeff1.value AS x_value
    FROM x_projections coeff0
    JOIN x_projections coeff1
        ON coeff0.constraint_id = coeff1.constraint_id
        AND coeff0.dimension = 0
        AND coeff1.dimension = 1
),
x_intervals AS (
    SELECT
        x_value AS interval_start,
        x_value AS interval_end
    FROM x_values

    UNION ALL

    SELECT
        a.x_value AS interval_start,
        MIN(b.x_value) AS interval_end
    FROM x_values a
    JOIN x_values b ON b.x_value > a.x_value
    GROUP BY a.x_value

    UNION ALL

    -- Artifical lower and upper interval.
    SELECT '-infinity'::DOUBLE, MIN(x_value) FROM x_values
    UNION ALL
    SELECT MAX(x_value), '+infinity'::DOUBLE FROM x_values

    ORDER BY interval_start, interval_end
),
-- Take a sample point from each interval (halfway in between).
sample_points AS (
    SELECT
        CASE
            WHEN ISINF(interval_start) THEN interval_end - 1.0
            WHEN ISINF(interval_end) THEN interval_start + 1.0
            ELSE (interval_start + interval_end) / 2.0
        END AS sample_point
    FROM x_intervals
),
-- Make a Coefficient-compatible representation of the sample points.
sample_input_values AS (
    SELECT ROW_NUMBER() over () AS input_id, 0 AS dimension, 1.0 AS value
    FROM sample_points

    UNION ALL

    SELECT ROW_NUMBER() over () AS input_id, 1 AS dimension, sample_point AS value
    FROM sample_points
),
-- Now we start lifting back up.
-- We first need all xy_projections. Now we normalize to y=-1 so we can simply
-- sum the preceding coeffs*sample_points.
x_lift_normalized AS (
    SELECT
        xyp.constraint_id,
        xyp.dimension,
        xyp.value  / -ld.value AS value
    FROM xy_projections xyp
    JOIN xy_projections ld
        ON xyp.constraint_id = ld.constraint_id
        AND ld.dimension = 2
        AND xyp.dimension < 2
),
x_lift_y_eval AS (
    SELECT
        i.input_id,
        SUM(i.value * xl.value) AS y_value
    FROM x_lift_normalized xl
    JOIN sample_input_values i
        ON xl.dimension = i.dimension
    GROUP BY i.input_id, xl.constraint_id
),
y_inputs AS (
    SELECT
        input_id,
        y_value
    FROM x_lift_y_eval
    GROUP BY input_id, y_value
),
y_intervals AS (
    SELECT
        input_id,
        y_value AS interval_start,
        y_value AS interval_end
    FROM y_inputs

    UNION ALL

    SELECT
        a.input_id,
        a.y_value AS interval_start,
        MIN(b.y_value) AS interval_end,
    FROM y_inputs a
    JOIN y_inputs b ON a.input_id = b.input_id
        AND b.y_value > a.y_value
    GROUP BY a.input_id, a.y_value

    UNION ALL

    SELECT
        input_id,
        '-infinity'::DOUBLE,
        MIN(y_value)
    FROM y_inputs
    GROUP BY input_id

    UNION ALL

    SELECT
        input_id,
        MAX(y_value),
        '+infinity'::DOUBLE,
    FROM y_inputs
    GROUP BY input_id
),
y_sample_points AS (
    SELECT
        input_id,
        ROW_NUMBER() over (PARTITION BY input_id ORDER BY interval_start) AS id,
        CASE
            WHEN ISINF(interval_start) THEN interval_end - 1.0
            WHEN ISINF(interval_end) THEN interval_start + 1.0
            ELSE (interval_start + interval_end) / 2.0
        END AS value
    FROM y_intervals
),
xy_input_values AS (
    SELECT
        -- The combination input_id (x-value) and id (of the y-value) becomes
        -- the new input ID. This way we can group on it later on, and preserve
        -- the link with the x input that generated the y.
        'x' || s.input_id || 'y' || y.id AS input_id,
        s.dimension,
        s.value
    FROM sample_input_values s
    JOIN y_sample_points y ON s.input_id = y.input_id

    UNION ALL

    SELECT
        'x' || input_id || 'y' || id AS input_id,
        2 AS dimension,
        value
    FROM y_sample_points
),
y_lift_normalized AS (
    -- We already have constraints involving z normalized to a2=1, so simply
    -- multiply by -1
    SELECT
        constraint_id,
        dimension,
        -value AS value
    FROM zprojection_normalized_constraints
),
y_lift_z_eval AS (
    SELECT
        i.input_id,
        SUM(i.value * yl.value) AS z_value
    FROM y_lift_normalized yl
    JOIN xy_input_values i
        ON yl.dimension = i.dimension
    GROUP BY i.input_id, yl.constraint_id
),
z_inputs AS (
    SELECT
        input_id,
        ROW_NUMBER() over (PARTITION BY input_id ORDER BY z_value) AS id,
        z_value
    FROM y_lift_z_eval
    GROUP BY input_id, z_value
),
xyz_input_values AS (
    SELECT
        i.input_id || 'z' || z.id AS input_id,
        i.dimension,
        i.value
    FROM xy_input_values i
    JOIN z_inputs z ON i.input_id = z.input_id

    UNION ALL

    SELECT
        input_id || 'z' || id AS input_id,
        3 AS dimension,
        z_value AS value
    FROM z_inputs
),
results AS (
    SELECT
        c.constraint_id,
        lc.description,
        i.input_id,
        SUM(i.value * c.value) AS result
    FROM xyz_input_values i
    JOIN Coefficient c ON i.dimension = c.dimension
    JOIN LinearConstraint lc ON c.constraint_id = lc.id
    GROUP BY c.constraint_id, i.input_id, lc.description
),
sat_input_ids AS (
    SELECT input_id FROM results WHERE description = 'z-2' AND result > 0
    -- INTERSECT for AND, UNION for OR.
    INTERSECT
    SELECT input_id FROM results WHERE description = 'x-2' AND result < 0
    INTERSECT
    SELECT input_id FROM results WHERE description = 'y-2' AND result < 0
),
solutions AS (
    SELECT * FROM xyz_input_values
    NATURAL JOIN sat_input_ids
    WHERE dimension > 0
    ORDER BY dimension
)
SELECT * FROM solutions;

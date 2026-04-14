WITH RECURSIVE
highest_dimension AS (
    SELECT MAX(dimension) AS dimension FROM Coefficient
),
coefficients_with_constraint_dimension AS (
    SELECT
        c.constraint_id,
        c.dimension,
        c.value,
        -- This is a window function for convenience; can be rewritten to a join
        -- or something if needed.
        MAX(dimension) OVER (PARTITION BY constraint_id) AS constraint_dimension
    FROM Coefficient c
),
dimensions AS (
    SELECT DISTINCT dimension FROM coefficient
),
highest_dimension_normalized_constraints AS (
    SELECT
        c.constraint_id,
        c.dimension,
        c.value / hd_coeff.value AS value,
        c.constraint_dimension
    FROM coefficients_with_constraint_dimension c
    -- Only look at the highest dimension constraints.
    JOIN highest_dimension hd ON c.constraint_dimension = hd.dimension
    -- Join with the coeff of the highest dimension so we can normalize to e.g.
    -- z=1.
    JOIN Coefficient hd_coeff ON
        hd_coeff.constraint_id = c.constraint_id
        AND hd_coeff.dimension = c.constraint_dimension
        AND c.dimension < hd_coeff.dimension
        AND hd_coeff.value <> 0
),
highest_dimension_intersects AS (
    SELECT
        -- TODO: can also use array instead?
        (nc1.constraint_id || 'x' || nc2.constraint_id) AS constraint_id,
        nc1.dimension,
        nc2.value - nc1.value AS value,
        nc1.constraint_dimension - 1 AS constraint_dimension
    FROM highest_dimension_normalized_constraints nc1
    JOIN highest_dimension_normalized_constraints nc2
        ON nc1.constraint_id < nc2.constraint_id -- Unique pairs (i.e. only 1x3, not also 3x1)
        AND nc1.dimension = nc2.dimension
),
highest_dimension_projections AS (
    -- Constraints from lower dimensions
    SELECT
        constraint_id,
        dimension,
        value,
        constraint_dimension
    FROM coefficients_with_constraint_dimension
    WHERE constraint_id NOT IN
        (SELECT constraint_id FROM highest_dimension_normalized_constraints)
    UNION
    -- Combined with the intersections we just calculated
    SELECT
        constraint_id,
        dimension,
        value,
        constraint_dimension
    FROM highest_dimension_intersects hdi1
    -- Filter out impossible constraints (e.g. 2 +0x + 0y=0).
    WHERE EXISTS (
        SELECT 1
        FROM highest_dimension_intersects hdi2
        WHERE hdi1.constraint_id = hdi2.constraint_id
        AND hdi2.dimension > 0
        AND hdi2.value <> 0
    )
),
-- TODO: check this for correctness againts the hardcoded version.
recursive_projections AS (
    SELECT
        p.constraint_id,
        p.dimension,
        p.value,
        p.constraint_dimension AS constraint_dimension,
        hd.dimension AS projected_dimension
    FROM highest_dimension_projections p, highest_dimension hd

    UNION

    SELECT
        p.constraint_id,
        p.dimension,
        p.value,
        p.constraint_dimension AS constraint_dimension,
        p.projected_dimension
    FROM (
        WITH n_min_1_highest_dimension AS (
            SELECT MIN(projected_dimension) - 1 AS dimension
            FROM recursive_projections
            -- Stop at R1 (= x)
            WHERE dimension > 1
        ),
        normalized_constraints AS (
            SELECT
                c.constraint_id,
                c.dimension,
                c.value / hd_coeff.value AS value,
                c.constraint_dimension
            FROM recursive_projections c
            JOIN n_min_1_highest_dimension hd
                ON c.constraint_dimension = hd.dimension
                -- AND hd.dimension > 1
            JOIN recursive_projections hd_coeff
                ON hd_coeff.dimension = hd.dimension
                AND hd_coeff.constraint_id = c.constraint_id
                AND c.dimension < hd_coeff.dimension
                AND hd_coeff.value <> 0
        ),
        intersects AS (
            SELECT
                (nc1.constraint_id || 'x(' || nc2.constraint_id || ')') AS constraint_id,
                nc1.dimension,
                nc2.value - nc1.value AS value,
                nc1.constraint_dimension - 1 AS constraint_dimension
            FROM normalized_constraints nc1
            JOIN normalized_constraints nc2
                ON nc1.constraint_id < nc2.constraint_id
                AND nc1.dimension = nc2.dimension
        ),
        projections AS (
            -- Original constraints from lower dimensions.
            SELECT
                c.constraint_id,
                c.dimension,
                c.value,
                c.constraint_dimension
            FROM coefficients_with_constraint_dimension c
            JOIN n_min_1_highest_dimension hd
                ON c.constraint_dimension < hd.dimension
            WHERE c. constraint_id NOT IN
                (SELECT constraint_id FROM normalized_constraints)

            UNION

            -- Combined with the intersections we just calculated
            SELECT
                constraint_id,
                dimension,
                value,
                constraint_dimension
            FROM intersects hdi1
            -- Filter out impossible constraints (e.g. 2 + 0x + 0y=0).
            WHERE EXISTS (
                SELECT 1
                FROM intersects hdi2
                WHERE hdi1.constraint_id = hdi2.constraint_id
                AND hdi2.dimension > 0
                AND hdi2.value <> 0
            )
        )
        SELECT
            p.constraint_id,
            p.dimension,
            p.value,
            p.constraint_dimension AS constraint_dimension,
            hd.dimension AS projected_dimension
        FROM projections p, n_min_1_highest_dimension hd
    ) p
),
-- Now our projection is ready to calculate R1 (= x) values, and take sample
-- points from the intervals they define.
x_values AS (
    -- TODO: this can also be a group by I think.
    SELECT DISTINCT -coeff0.value / coeff1.value AS x_value
    FROM recursive_projections coeff0
    JOIN recursive_projections coeff1
        ON coeff0.constraint_id = coeff1.constraint_id
        AND coeff0.dimension = 0
        AND coeff1.dimension = 1
        AND coeff1.value <> 0
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
    ORDER BY interval_start, interval_end
),
-- Make a Coefficient-compatible representation of the sample points.
sample_input_values AS (
    SELECT ROW_NUMBER() over () AS input_id, 0 AS dimension, 1.0::DOUBLE AS value
    FROM sample_points

    UNION ALL

    SELECT ROW_NUMBER() over () AS input_id, 1 AS dimension, sample_point AS value
    FROM sample_points
),
recursive_lifts AS (
    SELECT
        -- Cast to varchar so we can build a unique "provenance" ID.
        CAST(input_id AS VARCHAR) AS input_id,
        dimension,
        value
    FROM sample_input_values

    UNION

    SELECT input_id, dimension, value
    FROM (
        WITH dim_n_plus_1 AS (
            SELECT MAX(dimension) + 1 AS dimension
            FROM recursive_lifts
        ),
        dim_n_plus_1_normalized_constraints AS (
            SELECT
                p.constraint_id,
                p.dimension,
                p.value / -pnd.value AS value
            FROM recursive_projections p
            CROSS JOIN dim_n_plus_1 nd
            JOIN recursive_projections pnd
                ON p.constraint_id = pnd.constraint_id
                AND pnd.dimension = nd.dimension
                AND p.dimension < nd.dimension
                AND pnd.value <> 0
        ),
        -- Input sample point eval'ed for each constraint.
        dim_n_plus_1_eval AS (
            SELECT
                i.input_id,
                SUM(i.value * n.value) AS value
            FROM dim_n_plus_1_normalized_constraints n
            JOIN recursive_lifts i
                ON n.dimension = i.dimension
            GROUP BY i.input_id, n.constraint_id
        ),
        dim_n_plus_1_intervals AS (
            SELECT
                input_id,
                value AS interval_start,
                value AS interval_end
            FROM dim_n_plus_1_eval
            GROUP BY input_id, value

            UNION

            SELECT
                a.input_id,
                a.value AS interval_start,
                MIN(b.value) AS interval_end
            FROM dim_n_plus_1_eval a
            JOIN dim_n_plus_1_eval b ON b.value > a.value
            GROUP BY a.input_id, a.value

            UNION

            -- Artifical lower and upper interval.
            SELECT input_id, '-infinity'::DOUBLE, MIN(value)
            FROM dim_n_plus_1_eval
            GROUP BY input_id
            HAVING MIN(value) IS NOT NULL

            UNION

            SELECT input_id, MAX(value), '+infinity'::DOUBLE
            FROM dim_n_plus_1_eval
            GROUP BY input_id
            HAVING MAX(value) IS NOT NULL
        ),
        dim_n_plus_1_sample_points AS (
            SELECT
                input_id,
                CASE
                    WHEN ISINF(interval_start) THEN interval_end - 1.0
                    WHEN ISINF(interval_end) THEN interval_start + 1.0
                    ELSE (interval_start + interval_end) / 2.0
                END AS value
            FROM dim_n_plus_1_intervals
        ),
        dim_n_plus_1_coeff AS (
            SELECT
                input_id,
                value,
                -- Set instance will be used to build the unique ID of the new sample
                -- point input.
                ROW_NUMBER() OVER(PARTITION BY input_id ORDER BY value) as idx
            FROM dim_n_plus_1_sample_points
        )
        SELECT
            -- Append a suffix to get unique IDs, but keep 1 version of the
            -- original ID (so we don't get duplicates).
            CASE
                WHEN c.idx = 1 THEN CAST(l.input_id AS VARCHAR)
                ELSE l.input_id || '.' || (c.idx - 1)
            END AS input_id,
            l.dimension,
            l.value
        FROM recursive_lifts l
        JOIN dim_n_plus_1_coeff c ON l.input_id = c.input_id

        UNION ALL

        SELECT
            CASE
                WHEN c.idx = 1 THEN CAST(c.input_id AS VARCHAR)
                ELSE c.input_id || '.' || (c.idx - 1)
            END,
            d.dimension,
            c.value
        FROM dim_n_plus_1_coeff c
        CROSS JOIN dim_n_plus_1 d
    )
),
-- Now finally calculate the highest dimension values. We could also include
-- this in recursive_lifts, but then we'd end up with more points than we
-- actually need (since we'd be sampling from the intervals, where we only
-- really need the sections).
--
-- We already have the normalized constraints, but normalized to z=1 instead of
-- z=-1 (if z is the highest dimension).
highest_dimension_negative_normalized_constraints AS (
    SELECT
        constraint_id,
        dimension,
        -value AS value,
        constraint_dimension -- Not needed?
    FROM highest_dimension_normalized_constraints
),
highest_dimension_eval AS (
    SELECT
        i.input_id,
        SUM(i.value * n.value) AS value
    FROM highest_dimension_negative_normalized_constraints n
    JOIN recursive_lifts i
        ON n.dimension = i.dimension
    GROUP BY i.input_id, n.constraint_id
),
-- Combine it again
highest_dimension_coeff AS (
    SELECT
        input_id,
        value,
        -- Set instance will be used to build the unique ID of the new sample
        -- point input.
        ROW_NUMBER() OVER(PARTITION BY input_id ORDER BY value) as idx
    FROM highest_dimension_eval
),
-- A collection of all points we got from following the lift up, including the
-- highest dimension.
all_cad_points AS (
    SELECT
        CASE
            WHEN c.idx = 1 THEN CAST(l.input_id AS VARCHAR)
            ELSE l.input_id || '.' || (c.idx - 1)
        END AS input_id,
        l.dimension,
        l.value
    FROM recursive_lifts l
    JOIN highest_dimension_coeff c ON l.input_id = c.input_id

    UNION ALL

    SELECT
        CASE
            WHEN c.idx = 1 THEN CAST(c.input_id AS VARCHAR)
            ELSE c.input_id || '.' || (c.idx - 1)
        END,
        hd.dimension,
        c.value
    FROM highest_dimension_coeff c
    CROSS JOIN highest_dimension hd
),
results AS (
    SELECT
        c.constraint_id,
        lc.description,
        i.input_id,
        SUM(i.value * c.value) AS result
    FROM all_cad_points i
    JOIN Coefficient c ON i.dimension = c.dimension
    JOIN LinearConstraint lc ON c.constraint_id = lc.id
    GROUP BY c.constraint_id, i.input_id, lc.description
),
sat_input_ids AS (
    SELECT input_id FROM results WHERE description = 'u-2' AND result > 0
    -- INTERSECT for AND, UNION for OR.
    INTERSECT
    SELECT input_id FROM results WHERE description = 'x-4' AND result < 0
    INTERSECT
    SELECT input_id FROM results WHERE description = 'y-4' AND result < 0
    INTERSECT
    SELECT input_id FROM results WHERE description = 'z-2' AND result > 0
),
solutions AS (
    SELECT * FROM all_cad_points
    NATURAL JOIN sat_input_ids
    WHERE dimension > 0
    ORDER BY dimension
)
SELECT * FROM solutions
ORDER BY input_id, dimension;

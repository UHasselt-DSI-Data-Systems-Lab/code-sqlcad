WITH RECURSIVE
constraints_with_dimension AS (
    SELECT
        id,
        description,
        a0, a1, a2, a3, a4,
        CASE
            WHEN a4 <> 0 THEN 4
            WHEN a3 <> 0 THEN 3
            WHEN a2 <> 0 THEN 2
            WHEN a1 <> 0 THEN 1
            ELSE 0
        END as constraint_dimension
    FROM LinearConstraint
),
highest_dim AS (
    SELECT MAX(constraint_dimension) AS dimension
    FROM constraints_with_dimension
),
projections AS (
    SELECT
        CAST(id AS VARCHAR) AS id,
        a0, a1, a2, a3, a4,
        constraint_dimension, 4 AS dim_to_project
    FROM constraints_with_dimension

    UNION

    SELECT
        id,
        a0, a1, a2, a3, a4,
        constraint_dimension,
        dim_to_project
    FROM (
        WITH dim_n AS (
            SELECT MIN(dim_to_project) AS dimension
            FROM projections
        ),
        dim_n_constraints AS (
            SELECT projections.*
            FROM projections
            CROSS JOIN dim_n
            WHERE constraint_dimension = dim_n.dimension
        ),
        dim_n_intersects AS (
            SELECT
                ('x' || a.id || ' ' || b.id) AS id,
                CASE
                    WHEN a.dim_to_project = 4 THEN (a.a0 / a.a4) - (b.a0 / b.a4)
                    WHEN a.dim_to_project = 3 THEN (a.a0 / a.a3) - (b.a0 / b.a3)
                    WHEN a.dim_to_project = 2 THEN (a.a0 / a.a2) - (b.a0 / b.a2)
                    WHEN a.dim_to_project = 1 THEN (a.a0 / a.a1) - (b.a0 / b.a1)
                    ELSE 0
                END AS a0,
                CASE
                    WHEN a.dim_to_project = 4 THEN (a.a1 / a.a4) - (b.a1 / b.a4)
                    WHEN a.dim_to_project = 3 THEN (a.a1 / a.a3) - (b.a1 / b.a3)
                    WHEN a.dim_to_project = 2 THEN (a.a1 / a.a2) - (b.a1 / b.a2)
                    ELSE 0
                END AS a1,
                CASE
                    WHEN a.dim_to_project = 4 THEN (a.a2 / a.a4) - (b.a2 / b.a4)
                    WHEN a.dim_to_project = 3 THEN (a.a2 / a.a3) - (b.a2 / b.a3)
                    ELSE 0
                END AS a2,
                CASE
                    WHEN a.dim_to_project = 4 THEN (a.a3 / a.a4) - (b.a3 / b.a4)
                    ELSE 0
                END AS a3,
                0 AS a4,
                a.constraint_dimension - 1 AS dim_to_project
            FROM dim_n_constraints a
            JOIN dim_n_constraints b
                ON a.id < b.id
        ),
        dim_n_intersects_with_cd AS (
            SELECT
                *,
                CASE
                    WHEN a3 <> 0 THEN 3
                    WHEN a2 <> 0 THEN 2
                    WHEN a1 <> 0 THEN 1
                    ELSE 0
                END AS constraint_dimension
            FROM dim_n_intersects
            -- Filter out planes that do not intersect.
            WHERE a1 <> 0 OR a2 <> 0 OR a3 <> 0 OR a4 <> 0
        )
        SELECT
            id,
            a0, a1, a2, a3, a4,
            constraint_dimension,
            dim_to_project
        FROM dim_n_intersects_with_cd
        UNION
        SELECT
            id,
            a0, a1, a2, a3, a4,
            constraint_dimension,
            dim_to_project - 1
        FROM projections
        WHERE constraint_dimension < dim_to_project
    )
    WHERE dim_to_project > 0
),
x_values AS (
    SELECT DISTINCT -a0/a1 AS value
    FROM projections
    WHERE dim_to_project = 1
    AND a1 <> 0
),
-- Intervals + sample points in one go.
sample_points AS (
    SELECT
        value AS sample_point
    FROM x_values

    UNION

    SELECT
        (a.value + MIN(b.value)) / 2
    FROM x_values a
    JOIN x_values b ON b.value > a.value
    GROUP BY a.value

    UNION

    -- Artifical lower and upper interval.
    SELECT MIN(value) - 1 FROM x_values
    UNION
    SELECT MAX(value) + 1 FROM x_values
),
lifts AS (
    SELECT
        1 AS dim_to_lift,
        sample_point AS x1,
        0::DOUBLE AS x2,
        0::DOUBLE AS x3,
        0::DOUBLE AS x4
    FROM sample_points

    UNION

    SELECT dim_to_lift, x1, x2, x3, x4 FROM
    (
        WITH dim_n_plus_1 AS (
            SELECT MAX(dim_to_lift) + 1 AS dimension
            FROM lifts
            HAVING MAX(dim_to_lift) < 4
        ),
        dim_n_plus_1_eval AS (
            SELECT
                l.x1 AS x1,
                CASE
                    WHEN d.dimension = 2
                    THEN (p.a0 / -p.a2) + (p.a1 * l.x1 / -p.a2)
                    ELSE l.x2
                END AS x2,
                CASE
                    WHEN d.dimension = 3
                    THEN (p.a0 / -p.a3)
                        + (p.a1 * l.x1 / -p.a3)
                        + (p.a2 * l.x2 / -p.a3)
                    ELSE l.x3
                END AS x3,
                CASE
                    WHEN d.dimension = 4
                    THEN (p.a0 / -p.a4)
                        + (p.a1 * l.x1 / -p.a4)
                        + (p.a2 * l.x2 / -p.a4)
                        + (p.a3 * l.x3 / -p.a4)
                    ELSE l.x4
                END AS x4,
                l.dim_to_lift + 1 AS dim_to_lift
            FROM lifts l
            CROSS JOIN dim_n_plus_1 d
            JOIN projections p
                ON p.dim_to_project = d.dimension
                AND p.constraint_dimension = d.dimension
            WHERE l.dim_to_lift = d.dimension - 1
            GROUP BY
                d.dimension, dim_to_lift,
                l.x1, l.x2, l.x3, l.x4,
                p.a0, p.a1, p.a2, p.a3, p.a4
        )
        -- New sample points
        SELECT
            dim_to_lift,
            x1,
            x2,
            x3,
            x4
        FROM dim_n_plus_1_eval
        GROUP BY dim_to_lift, x1, x2, x3, x4

        UNION

        SELECT
            a.dim_to_lift,
            a.x1,
            CASE
                WHEN a.dim_to_lift = 2
                THEN (a.x2 + MIN(b.x2)) / 2
                ELSE a.x2
            END AS x2,
            CASE
                WHEN a.dim_to_lift = 3
                THEN (a.x3 + MIN(b.x3)) / 2
                ELSE a.x3
            END AS x3,
            CASE
                WHEN a.dim_to_lift = 4
                THEN (a.x4 + MIN(b.x4)) / 2
                ELSE a.x4
            END AS x4
        FROM dim_n_plus_1_eval a
        JOIN dim_n_plus_1_eval b
            ON
                (
                    a.x1 = b.x1
                    AND IF(a.dim_to_lift > 2, a.x2 = b.x2, true)
                    AND IF(a.dim_to_lift > 3, a.x3 = b.x3, true)
                    AND IF(a.dim_to_lift > 4, a.x4 = b.x4, true)
                )
            AND
                CASE
                    WHEN a.dim_to_lift = 2 THEN b.x2 > a.x2
                    WHEN a.dim_to_lift = 3 THEN b.x3 > a.x3
                    WHEN a.dim_to_lift = 4 THEN b.x4 > a.x4
                END
        GROUP BY
            a.x1, a.x2, a.x3, a.x4,
            a.dim_to_lift

        UNION

        SELECT
            dim_to_lift,
            x1,
            CASE
                WHEN dim_to_lift = 2
                THEN MIN(x2) - 1
                ELSE x2
            END AS x2,
            CASE
                WHEN dim_to_lift = 3
                THEN MIN(x3) - 1
                ELSE x3
            END AS x3,
            CASE
                WHEN dim_to_lift = 4
                THEN MIN(x4) - 1
                ELSE x4
            END AS x4
        FROM dim_n_plus_1_eval
        GROUP BY x1, x2, x3, x4, dim_to_lift

        UNION

        SELECT
            dim_to_lift,
            x1,
            CASE
                WHEN dim_to_lift = 2
                THEN MAX(x2) + 1
                ELSE x2
            END AS x2,
            CASE
                WHEN dim_to_lift = 3
                THEN MAX(x3) + 1
                ELSE x3
            END AS x3,
            CASE
                WHEN dim_to_lift = 4
                THEN MAX(x4) + 1
                ELSE x4
            END AS x4
        FROM dim_n_plus_1_eval
        GROUP BY x1, x2, x3, x4, dim_to_lift
    )
),
results AS (
    SELECT
        id,
        description,
        x1, x2, x3, x4,
        a0 + a1*x1 + a2*x2 + a3*x3 + a4*x4 AS result
    FROM LinearConstraint lc
    CROSS JOIN highest_dim d
    JOIN lifts
        -- Or
        ON lifts.dim_to_lift = d.dimension
),
solutions AS (
    -- "Compilation" of FO formula
    (
        (
            SELECT x1, x2, x3, x4 FROM results WHERE description = 'x+y+z' AND result < 0
            INTERSECT
            SELECT x1, x2, x3, x4 FROM results WHERE description = 'u' AND result = 0
        )
        UNION
        (
            SELECT x1, x2, x3, x4 FROM results WHERE description = 'x+y+z' AND result >= 0
            INTERSECT
            SELECT x1, x2, x3, x4 FROM results WHERE description = 'x+y+z-u' AND result = 0
        )
    )
    INTERSECT
    SELECT x1, x2, x3, x4 FROM results WHERE description = 'u-3' AND result > 0
    INTERSECT
    SELECT x1, x2, x3, x4 FROM results WHERE description = 'x-3' AND result < 0
    INTERSECT
    SELECT x1, x2, x3, x4 FROM results WHERE description = 'y-3' AND result < 0
    INTERSECT
    SELECT x1, x2, x3, x4 FROM results WHERE description = 'z-3' AND result < 0
)

SELECT * FROM solutions
ORDER BY x1, x2, x3, x4;

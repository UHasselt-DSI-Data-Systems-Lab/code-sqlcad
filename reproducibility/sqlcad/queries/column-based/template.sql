WITH RECURSIVE
constraints_with_dimension AS (
    SELECT
        id,
        description,
        {all_coeff_columns},
        {constraint_dimension_definition}
        AS constraint_dimension
    FROM LinearConstraint
),
highest_dim AS (
    SELECT MAX(constraint_dimension) AS dimension
    FROM constraints_with_dimension
),
projections AS (
    SELECT
        CAST(id AS VARCHAR) AS id,
        {all_coeff_columns},
        constraint_dimension,
        {max_dimension} AS dim_to_project
    FROM constraints_with_dimension

    UNION

    SELECT
        id,
        {all_coeff_columns},
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
                {intersect_norm_and_calc},
                a.constraint_dimension - 1 AS dim_to_project
            FROM dim_n_constraints a
            JOIN dim_n_constraints b
                ON a.id < b.id
        ),
        dim_n_intersects_with_cd AS (
            SELECT
                *,
                {intersects_with_cd} AS constraint_dimension
            FROM dim_n_intersects
            -- Filter out planes that do not intersect.
            WHERE {intersect_filter}
        )
        SELECT
            id,
            {all_coeff_columns},
            constraint_dimension,
            dim_to_project
        FROM dim_n_intersects_with_cd
        UNION
        SELECT
            id,
            {all_coeff_columns},
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
        {default_vars}
    FROM sample_points

    UNION

    SELECT dim_to_lift, {all_vars} FROM
    (
        WITH dim_n_plus_1 AS (
            SELECT MAX(dim_to_lift) + 1 AS dimension
            FROM lifts
            HAVING MAX(dim_to_lift) < {max_dimension}
        ),
        dim_n_plus_1_eval AS (
            SELECT
                l.x1 AS x1,
                {lift_calculate_variables}
                l.dim_to_lift + 1 AS dim_to_lift
            FROM lifts l
            CROSS JOIN dim_n_plus_1 d
            JOIN projections p
                ON p.dim_to_project = d.dimension
                AND p.constraint_dimension = d.dimension
            WHERE l.dim_to_lift = d.dimension - 1
            GROUP BY
                d.dimension, dim_to_lift,
                {all_coeff_columns_prefixed},
                {all_vars_prefixed}
        )
        -- New sample points
        SELECT
            dim_to_lift,
            {all_vars}
        FROM dim_n_plus_1_eval
        GROUP BY dim_to_lift, {all_vars}

        UNION

        SELECT
            a.dim_to_lift,
            a.x1,
            {sample_points_calc}
        FROM dim_n_plus_1_eval a
        JOIN dim_n_plus_1_eval b
            ON
                (
                    a.x1 = b.x1
                    {sample_points_join_1}
                )
            AND
                {sample_points_join_2}
        GROUP BY
            {all_vars_prefixed_a},
            a.dim_to_lift

        UNION

        SELECT
            dim_to_lift,
            x1,
            {lift_min_infinity_calc}
        FROM dim_n_plus_1_eval
        GROUP BY {all_vars}, dim_to_lift

        UNION

        SELECT
            dim_to_lift,
            x1,
            {lift_plus_infinity_calc}
        FROM dim_n_plus_1_eval
        GROUP BY {all_vars}, dim_to_lift
    )
),
results AS (
    SELECT
        id,
        description,
        {all_vars},
        {sum_all_vars_times_all_coeffs} AS result
    FROM LinearConstraint lc
    CROSS JOIN highest_dim d
    JOIN lifts
        -- Or
        ON lifts.dim_to_lift = d.dimension
),
solutions AS (
    {compiled_formula}
)

SELECT * FROM solutions
ORDER BY {all_vars};

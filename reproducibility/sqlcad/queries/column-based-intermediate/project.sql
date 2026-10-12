WITH
dim_n_intersects AS (
    SELECT
        {intersect_calculation_coeffs}
    FROM {proj_n_plus_1} a
    JOIN {proj_n_plus_1} b
        ON a.id < b.id
        AND a.constraint_dimension = {dimension_to_project}
        AND b.constraint_dimension = {dimension_to_project}
),
dim_n_intersects_with_cd AS (
    SELECT
        {all_coeffs},
        {constraint_dimension_calc} AS constraint_dimension
    FROM dim_n_intersects
    WHERE {empty_intersect_filter}
),
with_previous AS (
    SELECT
        constraint_dimension,
        {all_coeffs}
    FROM dim_n_intersects_with_cd

    UNION ALL

    -- Union the original constraints of a lower dimension.
    SELECT
        constraint_dimension,
        {all_coeffs}
    FROM LinearConstraint
    WHERE constraint_dimension < {dimension_to_project}
),
unique_constraints AS (
    SELECT
        constraint_dimension,
        {normalized_coeffs}
    FROM with_previous
    GROUP BY ALL -- Remove duplicates
)
SELECT
    ROW_NUMBER() OVER() AS id,
    constraint_dimension,
    {all_coeffs}
FROM unique_constraints

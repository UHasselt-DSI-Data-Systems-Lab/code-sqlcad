WITH
dim_n_plus_1_eval AS (
    SELECT
        {lift_n_min_1_alias}.id AS base_cell_id,
        {lift_eval}
    FROM Lift_Dimension1 l1
    {lift_joins}
    JOIN {proj_n_plus_1} p
        ON p.constraint_dimension = {dimension}
    GROUP BY
        {lift_n_min_1_alias}.id,
        {lxvals_upto_nmin1},
        {p_a_vals}
),
new_sample_points AS (
    SELECT
        base_cell_id,
        x{dimension}
    FROM dim_n_plus_1_eval
    GROUP BY base_cell_id, x{dimension}

    UNION

    SELECT
        base_cell_id,
        x{dimension}
    FROM (
        SELECT
            a.base_cell_id,
            (a.x{dimension} + LEAD(a.x{dimension}) OVER (PARTITION BY a.base_cell_id ORDER BY a.x{dimension})) / 2 AS x{dimension}
        FROM dim_n_plus_1_eval a
    )
    WHERE x{dimension} IS NOT NULL

    UNION

    SELECT
        base_cell_id,
        MIN(x{dimension}) - 1
    FROM dim_n_plus_1_eval
    GROUP BY base_cell_id

    UNION

    SELECT
        base_cell_id,
        MAX(x{dimension}) + 1
    FROM dim_n_plus_1_eval
    GROUP BY base_cell_id
),
-- If we have a single interval for a cell (-inf to +inf), we need to add 0 as a
-- sample point in a separate step, since the min/max from the query above
-- returns zero rows.
new_sample_points_with_single_intervals AS (
    SELECT base_cell_id, x{dimension}
    FROM new_sample_points

    UNION

    SELECT {lift_n_min_1}.id, 0 AS x{dimension}
    FROM {lift_n_min_1}
    WHERE NOT EXISTS (
        SELECT 1
        FROM new_sample_points p
        WHERE p.base_cell_id = {lift_n_min_1}.id
    )
)
SELECT
    ROW_NUMBER() OVER (ORDER BY base_cell_id, x{dimension}) AS id,
    base_cell_id,
    x{dimension}
FROM new_sample_points_with_single_intervals

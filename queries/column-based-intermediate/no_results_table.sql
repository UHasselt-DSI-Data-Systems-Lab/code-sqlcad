WITH results_r{highest_dim} AS (
    SELECT
        l{highest_dim}.id AS cell_id,
        l{highest_dim}.base_cell AS base_cell,
        {compiled_query} AS truth_value
    FROM Lift_Dimension1 AS l1
{lift_joins}
{constraint_joins}
)

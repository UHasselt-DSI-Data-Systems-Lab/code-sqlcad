
SELECT
    {highest_lift_alias}.id AS cell_id,
    {compiled_query} AS truth_value
FROM Lift_Dimension1 AS l1
{lift_joins}
{constraint_joins}

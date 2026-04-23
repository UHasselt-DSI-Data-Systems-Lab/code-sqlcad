WITH
    input_nodes AS (
        SELECT
            id
        FROM
            node
        WHERE
            id NOT IN (
                SELECT
                    dst
                FROM
                    edge
            )
    ),
    output_nodes AS (
        SELECT
            id
        FROM
            node
        WHERE
            id NOT IN (
                SELECT
                    src
                FROM
                    edge
            )
    ),
    hidden_nodes AS (
        SELECT
            id
        FROM
            node
        WHERE
            id NOT IN (
                SELECT
                    id
                FROM
                    input_nodes
                UNION
                SELECT
                    id
                FROM
                    output_nodes
            )
    ),
    breakpoint_values AS (
        SELECT
            (- n.bias) / e.weight AS break_x,
        FROM
            node n
            JOIN edge e ON e.dst = n.id
            JOIN input_nodes i ON e.src = i.id
            JOIN hidden_nodes h ON h.id = n.id
        WHERE
            e.weight <> 0
        GROUP BY
            break_x,
            n.id
        ORDER BY
            break_x
    ),
    breakpoints_unordered AS (
        (
            SELECT
                break_x
            FROM
                breakpoint_values
        )
        UNION
        -- Artificial first and last breakpoint for now. Could also at -inf,0 and
        -- +inf,0 as first and last breakpoint in a last step instead.
        (
            SELECT
                MIN(break_x) - 10.0 AS break_x
            FROM
                breakpoint_values
        )
        UNION
        (
            SELECT
                MAX(break_x) + 10.0 AS break_x
            FROM
                breakpoint_values
        )
    ),
    breakpoints AS (
        SELECT
            break_x,
            ROW_NUMBER() OVER (
                ORDER BY
                    break_x
            ) AS row_number
        FROM
            breakpoints_unordered
    ),
    input_values AS (
        SELECT
            break_x AS input_value
        FROM
            breakpoints
    ),
    t1 AS (
        SELECT
            v.input_value,
            GREATEST (0, n.bias + SUM(e.weight * v.input_value)) AS t1,
            e.dst AS id
        FROM
            edge e
            JOIN input_nodes i ON i.id = e.src
            JOIN node n ON e.dst = n.id
            CROSS JOIN input_values v
        GROUP BY
            v.input_value,
            e.dst,
            n.bias
    ),
    output_values AS (
        SELECT
            t1.input_value,
            n.bias + SUM(e.weight * t1.t1) AS output_value,
            e.dst AS output_node_id
        FROM
            edge e
            JOIN t1 ON t1.id = e.src
            JOIN node n ON e.dst = n.id
        GROUP BY
            t1.input_value,
            e.dst,
            n.bias
    ),
    breakpoint_pairs AS (
        SELECT
            u1.break_x AS x1,
            e1.output_value AS y1,
            u2.break_x AS x2,
            e2.output_value AS y2
        FROM
            breakpoints u1
            JOIN breakpoints u2 ON u1.row_number = u2.row_number - 1
            JOIN output_values e1 ON u1.break_x = e1.input_value
            JOIN output_values e2 ON u2.break_x = e2.input_value
    )
SELECT
    x1,
    x2,
    (y2 - y1) / (x2 - x1) AS slope,
    y1 - slope * x1 as intercept,
FROM
    breakpoint_pairs

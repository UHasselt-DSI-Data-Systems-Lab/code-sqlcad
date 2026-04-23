from pathlib import Path
import os
import util.formula as f

queries_dir = Path(os.path.dirname(os.path.realpath(__file__))) / "../queries/column-based-intermediate"
DEBUG=True

with open(queries_dir / 'project.sql', 'r', encoding='utf-8') as file:
    project_template = file.read()

with open(queries_dir / 'x_values.sql', 'r', encoding='utf-8') as file:
    x_values_query = file.read()

with open(queries_dir / 'lift.sql', 'r', encoding='utf-8') as file:
    lift_template = file.read()

with open(queries_dir / "results.sql", 'r', encoding='utf-8') as file:
    results_template = file.read()

with open(queries_dir / "../nn/geometric.sql", "r", encoding="utf-8") as file:
    geometric_query = file.read()

def write_query(filename, query):
    if DEBUG:
        with open(Path('build') / filename, 'w', encoding='utf-8') as f:
            f.write(query)

def project_n(n, max_dim):
    intersect_calculation_coeffs = ""
    for i in range(0, n):
        intersect_calculation_coeffs += f"(a.a{i} / a.a{n}) - (b.a{i} / b.a{n}) AS a{i},\n"

    constraint_dimension_calc = "CASE\n"
    for i in range(1, n):
        d = n - i
        constraint_dimension_calc += f"  WHEN a{d} <> 0 THEN {d}\n"
    constraint_dimension_calc += "END\n"

    empty_intersect_filter = " OR ".join(f"a{i} <> 0" for i in range(1, n))

    all_coeffs = ", ".join(f"a{i}" for i in range(0, n))

    proj_n_plus_1=f"Projection_Dimension{n+1}" if n < max_dim else "LinearConstraint"

    query = project_template.format(
        dimension_to_project=n,
        proj_n_plus_1=proj_n_plus_1,
        intersect_calculation_coeffs=intersect_calculation_coeffs,
        constraint_dimension_calc=constraint_dimension_calc,
        empty_intersect_filter=empty_intersect_filter,
        all_coeffs=all_coeffs
    )

    write_query(f"project_{n}.sql", query)

    return query

def calculate_x_values(con, max_dims):
    # For only 1 dimension, we haven't projected anything.
    start_table = 'LinearConstraint' if max_dims == 1 else 'Projection_Dimension2'
    query = x_values_query.format(start_table=start_table)

    write_query("x_values.sql", query)

    con.execute(f"INSERT INTO Lift_Dimension1(id, x1) {query}")
    con.sql("SELECT * FROM Lift_Dimension1 ORDER BY x1")

def lift_n(n, max_dimension):
    lift_eval = f"(p.a0 / -p.a{n})\n"
    for i in range(1, n):
        lift_eval += f"  + (p.a{i} * l{i}.x{i} / -p.a{n})\n"
    lift_eval += f"AS x{n},\n"

    self_join_conditions = [f"a.x{i} = b.x{i}" for i in range(1, n)]
    self_join_conditions = " AND ".join(self_join_conditions)

    proj_n_plus_1=f"Projection_Dimension{n+1}"
    if n >= max_dimension:
        proj_n_plus_1="LinearConstraint"

    lift_joins = ""
    if i > 1:
        for i in range(2, n):
            lift_joins += f"JOIN Lift_Dimension{i} l{i} ON l{i}.base_cell = l{i-1}.id \n"

    # TODO: some of these vars are no longer used after the rework.
    query = lift_template.format(
        lift_n_min_1=f"Lift_Dimension{n-1}",
        lift_n_min_1_alias=f"l{n-1}",
        proj_n_plus_1=proj_n_plus_1,
        dimension=n,
        lxvals_upto_nmin1=", ".join(f"l{i}.x{i}" for i in range(1, n)),
        lift_eval=lift_eval,
        lift_joins=lift_joins,
        l_x_vals=", ".join(f"l{i}.x{i}" for i in range(1, n)),
        p_a_vals=", ".join(f"p.a{i}" for i in range(0, n+1)),
        new_x_vals=", ".join(f"x{i}" for i in range(1, n+1)),
        new_x_val=f"x{n}",
        xvals_upto_nmin1=", ".join(f"x{i}" for i in range(1, n)),
        a_x_vals_upto_nmin1=", ".join(f"a.x{i}" for i in range(1, n)),
        a_x_vals_upto_n=", ".join(f"a.x{i}" for i in range(1, n + 1)),
        halfway_interval=f"(a.x{n} + MIN(b.x{n})) / 2 AS x{n}",
        self_join_conditions=self_join_conditions,
        gt_condition=f"b.x{n} > a.x{n}",
        interval_mininf=f"MIN(x{n}) - 1",
        interval_plusinf=f"MAX(x{n}) + 1"
    )

    write_query(f"lift_{n}.sql", query)

    return query

def generate_db_for_constraints(con, constraints):
    dimensions = len(constraints[0]) - 2

    # Drop all old tables.
    for (table_name,) in con.sql("SHOW TABLES").fetchall():
        if table_name.startswith("Projection_Dimension") or table_name.startswith("Lift_Dimension"):
            con.execute(f"DROP TABLE IF EXISTS {table_name}")

    con.sql("DROP TABLE IF EXISTS LinearConstraint")
    con.sql("DROP TABLE IF EXISTS Result")

    create_table_sql = """
        CREATE TABLE LinearConstraint(
            id INTEGER PRIMARY KEY,
            description VARCHAR NOT NULL,
            constraint_dimension INTEGER NOT NULL,
    """
    for i in range(0, dimensions):
        create_table_sql += f"a{i} DOUBLE DEFAULT 0.0,"

    create_table_sql += ")"

    con.sql(create_table_sql)

    result_create_table = """
        CREATE TABLE Result(
            cell_id INTEGER,
            truth_value BOOLEAN
        )
        """
    con.sql(result_create_table)

    # Create a table for each projection step and for each lift step.
    for i in range(1, dimensions):
        proj_table_name = f"Projection_Dimension{i}"

        proj_create_table = f"""
            CREATE TABLE {proj_table_name}(
            id INTEGER PRIMARY KEY,
            constraint_dimension INTEGER,
        """
        for dimension in range (0, i):
            proj_create_table += f"a{dimension} DOUBLE DEFAULT 0.0,"
        proj_create_table += ")"

        lift_table_name = f"Lift_Dimension{i}"

        lift_create_table = f"""
            CREATE TABLE {lift_table_name}(
                id INTEGER PRIMARY KEY,
                {'base_cell INTEGER,' if i > 1 else ''}
                x{i} DOUBLE
            )
        """

        con.execute(proj_create_table)
        con.execute(lift_create_table)

    insert_query = """
        INSERT INTO LinearConstraint(id, description, constraint_dimension,
    """
    insert_query += ", ".join(f"a{i}" for i in range(0, dimensions))
    insert_query += ") VALUES ("
    insert_query += ", ".join("?" for i in range(0, dimensions + 3))
    insert_query += ")"

    for id, constraint in enumerate(constraints, start=0):
        con.execute(insert_query, [id] + constraint)

def projection_phase(con, dimensions):
    for i in range(0, dimensions):
        project_step = dimensions + 1 - i
        con.sql(f"INSERT INTO Projection_Dimension{project_step} {project_n(project_step, dimensions + 1)}")

def lift_phase(con, dimensions):
    for i in range(2, dimensions + 2):
        con.sql(f"INSERT INTO Lift_Dimension{i} {lift_n(i, dimensions + 1)}")

def write_results(con, dimensions, constraints):
    calc = "a0"
    for i in range(1, dimensions+2):
        calc += f" + a{i}*x{i}"

    xvals = ", ".join(f"l{i}.x{i}" for i in range(1, dimensions+2))

    # For now we assume a simple AND between everything, actualy compilation
    # will have to follow.
    compiled_query_parts = []
    for i, constraint in enumerate(constraints):
        calc = f"lc{i}.a0"
        for d in range(1, dimensions+2):
            calc += f" + lc{i}.a{d}*x{d}"

        # This will also need to be actually compiled.
        op = '<' if '<' in constraint[0] else '>'

        compiled_query_parts.append(f"{calc} {op} 0")

    compiled_query = " AND ".join(compiled_query_parts)

    constraint_joins = ""
    for i, constraint in enumerate(constraints):
        constraint_joins += f"JOIN LinearConstraint lc{i} ON lc{i}.description = '{constraint[0]}'\n"

    lift_joins = ""
    for i in range(1, dimensions+1):
        lift_joins += f"JOIN Lift_Dimension{i+1} l{i+1} ON l{i+1}.base_cell = l{i}.id\n"

    query = results_template.format(
        xvals=xvals,
        highest_lift=f"Lift_Dimension{dimensions+1}",
        highest_lift_alias=f"l{dimensions+1}",
        compiled_query=compiled_query,
        constraint_joins=constraint_joins,
        lift_joins=lift_joins,
    )

    write_query("results.sql", query)

    con.sql(f"INSERT INTO Result(cell_id, truth_value) {query}")

def massage_constraints(constraints):
    """
    Ensures the constraint list is in a format we can insert into the database:
    - The constraint dimension is added for each constraint
    - The constraints are zero-padded up until the max dimension
    """
    max_dim = max(len(row) for row in constraints)

    result = []
    for row in constraints:
        trimmed_len = len(row)
        for val in reversed(row):
            if val == 0:
                trimmed_len -= 1
            else:
                break

        effective_val = trimmed_len - 2

        new_row = [row[0], effective_val] + row[1:]

        padding_needed = (max_dim + 1) - len(new_row)
        new_row.extend([0] * padding_needed)

        result.append(new_row)

    return result

def create_cad(con, constraints):
    massaged_constraints = massage_constraints(constraints)
    input_dimensions = len(massaged_constraints[0]) - 3

    # TODO: legacy-wise, we assumed "input dimensions", so the number of inputs
    # to our F(x1, x2, ...) formula we used in the examples... So this should
    # actually be +1'ed in all the query functions.
    input_dimensions -= 1

    generate_db_for_constraints(con, massaged_constraints)
    projection_phase(con, input_dimensions)
    calculate_x_values(con, input_dimensions + 1)
    lift_phase(con, input_dimensions)



def compile_qf_query(constraints, formula):
    qf_part = f.quantifier_free_part(formula)

    def find_constraint_matching_ineq(ineq):
        for cid, c in enumerate(constraints):
            if c[0] == str(ineq):
                return (cid, c)

        raise Exception('No matching constraint found for inequality')

    def compile_ineq(ineq):
        cid, coeffs = find_constraint_matching_ineq(ineq)
        coeffs = coeffs[1:] # Skip description

        expression_parts = []

        for dim, coeff in enumerate(coeffs):
            if coeff == 0:
                continue

            if dim == 0:
                expression_parts.append(f"lc{cid}.a0")
                continue

            expression_parts.append(f"lc{cid}.a{dim}*x{dim}")

        expression = " + ".join(expression_parts)
        expression += f" {ineq.operator} 0"

        return expression

    def go(formula):
        match formula:
            case f.Or(formulas):
                parts = [f"({go(f)})" for f in formulas]
                return " OR ".join(parts)
            case f.And(formulas):
                parts = [f"({go(f)})" for f in formulas]
                return " AND ".join(parts)
            case f.Not(formula=formula):
                return f"NOT ({go(formula)})"
            case f.InEq():
                return compile_ineq(formula)
            case _:
                return "x"


    return go(qf_part)

def compile_results_query(constraint_coefficients, formula):
    dimensions = max(len(c) - 3 for c in constraint_coefficients)

    compiled_query = compile_qf_query(constraint_coefficients, formula)

    constraint_joins = ""
    for cid, _ in enumerate(constraint_coefficients):
        constraint_joins += f"JOIN LinearConstraint lc{cid} ON lc{cid}.id = {cid}\n"

    lift_joins = ""
    for i in range(1, dimensions+1):
        lift_joins += f"JOIN Lift_Dimension{i+1} l{i+1} ON l{i+1}.base_cell = l{i}.id\n"

    query = results_template.format(
        highest_lift_alias=f"l{dimensions+1}",
        compiled_query=compiled_query,
        constraint_joins=constraint_joins,
        lift_joins=lift_joins,
    )

    write_query("results.sql", query)

    return query

def compile_qe_query(formula):
    """
SELECT BOOL_OR(truth_value) AS truth_value
FROM (
    SELECT l2.base_cell, BOOL_OR(r.truth_value) AS truth_value
    FROM (
        SELECT l3.base_cell, BOOL_OR(r.truth_value) AS truth_value
        FROM Result r
        JOIN Lift_Dimension3 l3 ON l3.id = r.cell_id
        GROUP BY l3.base_cell
    ) r
    JOIN Lift_Dimension2 l2 ON l2.id = r.base_cell
    GROUP BY l2.base_cell
) r
JOIN Lift_Dimension1 l1 ON l1.id = r.base_cell
"""

    def go(formula, depth):
        inner_formula = None

        match formula:
            case f.Forall(formula=frmla):
                aggregation_function = 'BOOL_AND'
                inner_formula = frmla
            case f.Exists(formula=frmla):
                aggregation_function = 'BOOL_OR'
                inner_formula = frmla
            case _:
                raise Exception("Unquantified formula; not implemented")

        match inner_formula:
            case f.Quantifier():
                is_last_quantifier = False
            case _:
                is_last_quantifier = True

        is_first_quantifier = depth == 0

        indent = "  " * depth

        if is_last_quantifier and is_first_quantifier:
            # Only a single quantifier
            return f"""
    SELECT {aggregation_function}(truth_value) AS truth_value
    FROM Result r
            """
        if is_last_quantifier:
            dim = depth + 1

            return f"""
{indent}SELECT
{indent}  l{dim}.base_cell,
{indent}  {aggregation_function}(r.truth_value) AS truth_value
{indent}FROM Result r
{indent}JOIN Lift_Dimension{dim} l{dim} ON l{dim}.id = r.cell_id
{indent}GROUP BY l{dim}.base_cell
            """
        elif is_first_quantifier:
            return f"""
{indent}SELECT {aggregation_function}(truth_value) AS truth_value
{indent}FROM (
{indent}  {go(formula.formula, depth + 1)}
{indent}) r
{indent}JOIN Lift_Dimension1 l1 ON l1.id = r.base_cell
            """

        else:
            dim = depth + 1

            return f"""
{indent}SELECT
{indent}  l{dim}.base_cell,
{indent}  {aggregation_function}(r.truth_value) AS truth_value
{indent}FROM (
{indent}  {go(formula.formula, depth + 1)}
{indent}) r
{indent}JOIN Lift_Dimension{dim} l{dim} ON l{dim}.id = r.base_cell
{indent}GROUP BY l{dim}.base_cell
            """

    query = go(formula, 0)
    write_query("qe.sql", query)

    return query


def get_geometric_representation(con, model_id):
    """
    Retrieves the geometric representation of a model with the given ID. This is
    placeholder; for now we only store and fetch 1 model in the database.
    """
    mapping = []

    for (x1, x2, slope, intercept) in con.execute(geometric_query).fetchall():
        mapping.append({'x1': x1, 'x2': x2, 'slope': slope, 'intercept': intercept})

    return mapping


def evaluate_formula(con, formula, function_name_to_model_id_mapping=None):
    if not function_name_to_model_id_mapping:
        function_name_to_model_id_mapping = {}

    nn_geom_mapping = {}
    for fname, model_id in function_name_to_model_id_mapping.items():
        nn_geom_mapping[fname] = get_geometric_representation(con, model_id)

    formula = f.compile_nn_function_calls(formula, nn_geom_mapping)
    formula = f.rename_vars(formula)
    formula = f.rewrite_implications(formula)

    constraint_coefficients = []
    for constraint in f.collect_constraints(formula):
        description = str(constraint)
        coeffs = f.coefficients(constraint)

        constraint_coefficients.append([description] + coeffs)

    create_cad(con, constraint_coefficients)
    results_query = compile_results_query(constraint_coefficients, formula)
    con.sql(f"INSERT INTO Result(cell_id, truth_value) {results_query}")

    qe_query = compile_qe_query(formula)

    return con.sql(qe_query)

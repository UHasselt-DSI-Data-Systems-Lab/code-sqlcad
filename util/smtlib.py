from pysmt.environment import Environment
from pysmt.smtlib.parser import get_formula
import util.formula as f
import util.sqlcad as sqlcad
from io import StringIO

def get_ineq_operator(formula):
    if formula.is_le():
        return '<='
    if formula.is_lt():
        return '<'
    if formula.is_equals():
        return '='
    if formula.is_le():
        return '>='
    if formula.is_lt():
        return '>'

    return None

def flipped_operator(operator):
    match operator:
        case '<=':
            return '>='
        case '<':
            return '>'
        case '>=':
            return '<='
        case '>':
            return '<'
        case '=':
            return '='

def is_ineq(formula):
    return get_ineq_operator(formula) is not None

def smtlib_to_sqlcad(formula):
    if formula.is_forall():
        last_formula = smtlib_to_sqlcad(formula.args()[0])

        for var in reversed(formula.quantifier_vars()):
            last_formula = f.Forall(var.symbol_name(), last_formula)

        return last_formula
    elif formula.is_exists():
        last_formula = smtlib_to_sqlcad(formula.args()[0])

        for var in reversed(formula.quantifier_vars()):
            last_formula = f.Exists(var.symbol_name(), last_formula)

        return last_formula
    elif is_ineq(formula):
        operator = get_ineq_operator(formula)
        args = formula.args()

        def is_zero(f):
            return f.is_constant(value=0)

        if len(args) != 2 or not (is_zero(args[0]) or is_zero(args[1])):
            raise Exception(f"Only (in)equalities of the form a0+a1x1+... < 0 are allowed. Given: {formula}")

        if is_zero(args[1]):
            return f.InEq(operator, smtlib_to_sqlcad(args[0]))

        return f.InEq(flipped_operator(operator), smtlib_to_sqlcad(args[1]))
    elif formula.is_plus():
        terms = [smtlib_to_sqlcad(term) for term in formula.args()]

        return f.Add(terms)
    elif formula.is_minus():
        terms = [smtlib_to_sqlcad(term) for term in formula.args()]

        return f.Sub(terms)
    elif formula.is_times():
        terms = [smtlib_to_sqlcad(term) for term in formula.args()]

        return f.Mult(terms)
    elif formula.is_symbol():
        return f.Var(formula.symbol_name())
    elif formula.is_constant():
        return f.Const(float(formula.constant_value()))
    elif formula.is_and():
        formulas = [smtlib_to_sqlcad(f) for f in formula.args()]

        return f.And(formulas)
    elif formula.is_or():
        formulas = [smtlib_to_sqlcad(f) for f in formula.args()]

        return f.Or(formulas)
    elif formula.is_not():
        return f.Not(smtlib_to_sqlcad(formula.args()[0]))
    elif formula.is_function_application():
        name = formula.function_name()
        args = [smtlib_to_sqlcad(f) for f in formula.args()]

        return f.Function(str(name), args)
    elif formula.is_implies():
        antecedent = smtlib_to_sqlcad(formula.args()[0])
        conclusion = smtlib_to_sqlcad(formula.args()[1])

        return f.Implies(antecedent, conclusion)
    else:
        raise Exception(f"Not implemented yet: {formula}")

def parse_from_file(smtlib_file):
    environment = Environment() # Needed to reset cache?
    with open(smtlib_file, 'r', encoding='utf-8') as f:
        formula = get_formula(f, environment=environment)

    return smtlib_to_sqlcad(formula)

def parse_from_string(formula):
    environment = Environment() # Needed to reset cache?
    formula = get_formula(StringIO(formula), environment=environment)

    return smtlib_to_sqlcad(formula)

def evaluate_smtlib_formula(con, smtlib_file, function_name_to_model_id_mapping=None):
    formula = parse_from_file(smtlib_file)
    print(f"Evaluating {formula}")

    return sqlcad.evaluate_formula(con, formula, function_name_to_model_id_mapping)

def evaluate_smtlib_formula_str(con, formula_input, function_name_to_model_id_mapping=None):
    formula = parse_from_string(formula_input)
    print(f"Evaluating {formula}")

    return sqlcad.evaluate_formula(con, formula, function_name_to_model_id_mapping)

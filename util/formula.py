from dataclasses import dataclass
from typing import List

class InvalidFormulaException(Exception):
    pass

class Term:
    def map(self, f):
        pass

@dataclass
class Var(Term):
    name: str

    def __repr__(self):
        return self.name

    def map(self, f):
        return f(self)

@dataclass
class Const(Term):
    value: float

    def __repr__(self):
        return str(self.value)

    def map(self, f):
        return f(self)

@dataclass
class Add(Term):
    terms: List[Term]

    def __repr__(self):
        return ' + '.join(str(term) for term in self.terms)

    def map(self, f):
        new_terms = [term.map(f) for term in self.terms]

        return f(Add(new_terms))

@dataclass
class Sub(Term):
    terms: List[Term]

    def __repr__(self):
        return ' - '.join(str(term) for term in self.terms)

    def map(self, f):
        new_terms = [term.map(f) for term in self.terms]

        return f(Sub(new_terms))

# Negation
@dataclass
class Neg(Term):
    term: Term

    def __repr__(self):
        return f"-{self.term}"

    def map(self, f):
        return f(Neg(self.term.map(f)))

class Mult(Term):
    terms: List[Term]

    def __repr__(self):
        return ' * '.join(str(term) for term in self.terms)

    def __init__(self, terms):
        num_vars = sum(1 for term in terms if isinstance(term, Var))
        if num_vars > 1:
            raise InvalidFormulaException("Multiplying two variables is not allowed in LRA")

        self.terms = terms

    def map(self, f):
        new_terms = [term.map(f) for term in self.terms]

        return f(Mult(new_terms))

@dataclass
class Function(Term):
    name: str
    arguments: List[Term]

    def __repr__(self):
        return f"{self.name}({",".join(str(a) for a in self.arguments)})"

    def map(self, f):
        new_args = [arg.map(f) for arg in self.arguments]

        return f(Function(self.name, new_args))

class Formula:
    def apply(self, f):
        pass

    def map(self, f):
        pass

# We always assume formulas are in the form a0 + a1x2 ... < 0 (or >, >= etc)
@dataclass
class InEq(Formula):
    operator: str # One of < > <= >= =
    left: Term

    def __repr__(self):
        return f"{self.left} {self.operator} 0"

    def map(self, f):
        return f(InEq(self.operator, self.left.map(f)))

class Quantifier(Formula):
    def map(self, f):
        pass

@dataclass
class Forall(Quantifier):
    variable: str
    formula: Formula

    def __repr__(self):
        return f"∀{self.variable} {self.formula}"

    def map(self, f):
        return f(Forall(self.variable, self.formula.map(f)))

@dataclass
class Exists(Quantifier):
    variable: str
    formula: Formula

    def __repr__(self):
        return f"∃{self.variable} {self.formula}"

    def map(self, f):
        return f(Exists(self.variable, self.formula.map(f)))

@dataclass
class Not(Formula):
    formula: Formula

    def __repr__(self):
        return f"¬({self.formula})"

    def map(self, f):
        return f(Not(self.formula.map(f)))

@dataclass
class And(Formula):
    formulas: List[Formula]

    def __repr__(self):
        return " ∧ ".join(f"({f})" for f in self.formulas)

    def map(self, f):
        new_formulas = [formula.map(f) for formula in self.formulas]

        return f(And(new_formulas))

@dataclass
class Or(Formula):
    formulas: List[Formula]

    def __repr__(self):
        return " ∨ ".join(f"({f})" for f in self.formulas)

    def map(self, f):
        new_formulas = [formula.map(f) for formula in self.formulas]

        return f(Or(new_formulas))


@dataclass
class Implies(Formula):
    antecedent: Formula
    conclusion: Formula

    def __repr__(self):
        return f"({self.antecedent}) ⟶ ({self.conclusion})"

    def map(self, f):
        return f(Implies(self.antecedent.map(f), self.conclusion.map(f)))


def assert_prenex_normalform(formula):
    # TODO
    pass


def rewrite_implications(formula):

    def map_fn(formula):
        match formula:
            case Implies(antecedent=antecedent, conclusion=conclusion):
                return Or([Not(antecedent), conclusion])
            case _:
                return formula

    return formula.map(map_fn)


def collect_vars(formula: Formula | Term):
    # Dict keeps insertion order; set does not. We want to keep the same
    # ordering as given in the formula, for readability.
    variables = {}

    def f(formula):
        match formula:
            case Var(name=name):
                variables[name] = name

    formula.map(f)

    return variables.keys()

def collect_constraints(formula: Formula | Term):
    constraints = {}

    def f(formula):
        match formula:
            case InEq():
                constraints[str(formula)] = formula

        return formula

    formula.map(f)

    return constraints.values()

def collect_quantified_vars(formula: Formula):
    variables = []

    def f (formula):
        match formula:
            case Forall(variable=variable):
                variables.append((variable, "forall"))
            case Exists(variable=variable):
                variables.append((variable, "exists"))

    formula.map(f)

    # Map works in leaf-first order, so reverse the result.
    return list(reversed(variables))

def get_variable_ordering(formula: Formula | Term):
    return [name for name,_ in get_variable_ordering_with_type(formula)]


def get_variable_ordering_with_type(formula: Formula | Term):
    all_vars = collect_vars(formula)
    quantified_vars = collect_quantified_vars(formula)
    quantified_var_names = [name for name,type in quantified_vars]
    free_vars = [(var,"free") for var in all_vars if var not in quantified_var_names]

    return free_vars + quantified_vars


def prefix_existential_quantifiers(formula: Formula | Term) -> Formula:
    variable_ordering = get_variable_ordering_with_type(formula)
    free_vars = [varname for varname,vartype in variable_ordering if vartype == 'free']

    for varname in reversed(free_vars):
        formula = Exists(varname, formula)

    return formula


def rename_vars(formula: Formula):
    ordered_vars = get_variable_ordering(formula)

    translation_mapping = {}
    for i, var in enumerate(ordered_vars, start=1):
        translation_mapping[var] = f"_x{i}"

    def translate(formula):
        match formula:
            case Var(name=name):
                return Var(translation_mapping[name])
            case Forall(variable=name, formula=f):
                return Forall(translation_mapping[name], f)
            case Exists(variable=name, formula=f):
                return Exists(translation_mapping[name], f)
            case _:
                return formula

    return formula.map(translate), translation_mapping

def coefficients(ineq):
    """
    Extracts the coefficients from an inequality. Assumes format a0 + a1x1 +
    ..., with xn as variable names.
    """
    coeffs = {0: 0}

    def varname_to_dim(varname):
        return int(varname[2:])

    match ineq.left:
        case Add():
            for term in ineq.left.terms:
                match term:
                    case Const(value=value):
                        coeffs[0] += value
                    case Var(name=name):
                        dim = varname_to_dim(name)
                        coeffs[dim] = 1
                    case Mult(terms=[Var(name=name), Const(value=value)]) | Mult(terms=[Const(value=value), Var(name=name)]):
                        dim = varname_to_dim(name)
                        coeffs[dim] = value
                    case Neg(Var(name=name)):
                        dim = varname_to_dim(name)
                        coeffs[dim] = -1
                    case _:
                        raise Exception(f"Unexpected inequality. Required format is a0 + a1*x1 + ..., with a_n consts. Got {ineq.left}")
        case Sub():
            for i, term in enumerate(ineq.left.terms):
                sign = -1 if i > 0 else 1

                match term:
                    case Const(value=value):
                        coeffs[0] += value * sign
                    case Var(name=name):
                        dim = varname_to_dim(name)
                        coeffs[dim] = sign
                    case Mult([Var(name=name), Const(value=value)]) | Mult([Const(value=value), Var(name=name)]):
                        dim = varname_to_dim(name)
                        coeffs[dim] = value * sign
                    case _:
                        raise Exception(f"Unexpected inequality. Required format is a0 + a1*x1 + ..., with a_n consts. Given: {term}")
        case Mult(terms=[Var(name=name), Const(value=value)]) | Mult(terms=[Const(value=value), Var(name=name)]):
            dim = varname_to_dim(name)
            coeffs[dim] = value
        case Var(name=name):
            dim = varname_to_dim(name)
            coeffs[dim] = 1
        case _:
            raise Exception(f"Unexpected inequality; expects a sum a0 + a1*x1 + ... Given: {ineq.left}")

    sorted_coeffs = []
    max_dim = max(coeffs.keys())

    for i in range(0, max_dim + 1):
        sorted_coeffs.append(coeffs.get(i, 0))

    return sorted_coeffs


def quantifier_free_part(formula):
    match formula:
        case Forall(formula=f) | Exists(formula=f):
            return quantifier_free_part(f)
        case _:
            return formula

def compile_nn_function_calls(formula, nn_geomrepr_mapping):
    """
    Only support function calls with 1 input and 1 output for now. The mapping
    should containt the function names as keys and their geometric
    representation as values.

    The function arguments should be variables (maybe constants as well, to
    check).

    Translates a formula to the conjunction of the compiled function calls and
    the original formula with the F(x) calls replaced with an output variable.
    E.g. F(x) > 10 becomes (F(x) = z) -> z > 10.

    """

    # Tuple with key function description and value the tuple output_var_name
    # and original function formula.
    function_calls = {}

    def collect_function(function):
        """
        Collects the function call and returns a unique output var that it can
        be replaced with. Identical functions return identical output names.
        """
        nonlocal function_calls

        if str(function) in function_calls:
            return function_calls[str(function)][0]

        idx = len(function_calls)
        output_var_name = f"_function_output_{idx}"
        function_calls[str(function)] = (output_var_name, function)

        return output_var_name

    def collect_and_replace_function_calls(formula):

        def map_fun(formula):
            match formula:
                case Function():
                    output_var_name = collect_function(formula)

                    return Var(output_var_name)
                case _:
                    return formula

        return formula.map(map_fun)

    def translate_function_call(function: Function, output_var_name: str):
        function_terms = []

        args = function.arguments
        if len(args) != 1:
            raise Exception("Only functions with one argument are supported.")

        if function.name not in nn_geomrepr_mapping:
            raise Exception(f"Unexpected function call {function}; function with name {function.name} not provided in mapping")

        for record in nn_geomrepr_mapping[function.name]:
            x1 = record['x1']
            x2 = record['x2']
            a0 = record['intercept']
            a1 = record['slope']

            segment = Or([
                # min/max constraint of line segment.
                Not(
                    And([
                        InEq('>=', Sub([args[0], Const(x1)])),
                        InEq('<', Sub([args[0], Const(x2)]))
                    ])
                ),
                # y = a0 + a1*x, so a0 + a1*x - y = 0
                InEq(
                    '=',
                    Add([
                        Const(a0),
                        Mult([Const(a1), args[0]]),
                        Neg(Var(output_var_name))
                    ]
                ))
            ])
            function_terms.append(segment)

        return And(function_terms)


    def replace_quantifier_free_part(quantified_formula, formula_to_insert):
        """
        Given a quantified formula, replace the quantifier free part of the
        formula with the `formula_to_insert`.
        """

        match quantified_formula:
            case Forall(variable=v, formula=f):
                if isinstance(f, Quantifier):
                    return Forall(v, replace_quantifier_free_part(f, formula_to_insert))
                else:
                    return Forall(v, formula_to_insert)
            case Exists(variable=v, formula=f):
                if isinstance(f, Quantifier):
                    return Exists(v, replace_quantifier_free_part(f, formula_to_insert))
                else:
                    return Exists(v, formula_to_insert)
            case _:
                raise Exception('Unquantified formula given')

    formula_with_function_calls_replaced = collect_and_replace_function_calls(formula)

    # There were no function calls to replace; nothing left to do.
    if not function_calls:
        return formula

    function_formulas = [
        translate_function_call(f, output_var_name)
        for output_var_name, f in function_calls.values()
    ]

    # We want to go to [F1(x) AND F2(x) ... AND FN(x)] -> p, where p is the
    # original formula without quantifiers.
    implication = Or([
        Not(And(function_formulas)),
        quantifier_free_part(formula_with_function_calls_replaced)]
    )

    # Now we introduce new quantifiers for the output vars and insert them after
    # the original quantifiers.
    inner_formula = implication
    for output_var_name, _ in reversed(function_calls.values()):
        inner_formula = Forall(output_var_name, inner_formula)

    return replace_quantifier_free_part(formula_with_function_calls_replaced, inner_formula)

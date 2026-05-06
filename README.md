# SQLCAD

Code accompanying the paper [A Database-Inspired Approach to Deciding Linear
Real
Arithmetic](https://documentserver.uhasselt.be/simple-search?query=A+Database-Inspired+Approach+to+Deciding+Linear+Real+Arithmetic&location=global).
The research is presented as a series of Jupyter notebooks. Each notebook is
self-documenting.

## Project Structure

The first few notebooks deal with implementing CAD in SQL:

- [1.1 Basic CAD](./1.1.cad_basic.ipynb): Basic example that implements CAD using
  a CTE. Mostly an introduction to our approach to CAD.
- [1.2 Column-based CAD](./1.2.column_based_approach.ipynb): An alternative approach where
  coefficients are represented as columns instead of rows.
- [1.3 Intermediate tables](./1.3.column_based_intermediate.ipynb): A
  column-based approach that stores intermediate results in separate table,
  stepping away from the recursive query.
- [1.4 Performance comparison](./1.4.performance.ipynb): Compares the
  performance of the discussed approaches.

The next notebooks use the CAD to solve LRA formulas in SQL:

- [2.1 Quantifiers](./2.1.quantifiers.ipynb): introductory quantifier
  elimination in SQL.
- [2.2 General approach](./2.2.general_approach.ipynb): general framework that
  accepts SMT-LIB formulas.
- [2.3 Verifying NNs](./2.3.nnv.ipynb): application to neural network
  verification.

If you are only interested in the main result, optionally skim [1.1 Basic
CAD](./1.1.cad_basic.ipynb) to see how we implemented CAD in SQL and skip to
[2.2 General approach](./2.2.general_approach.ipynb) to see the general
framework in action.

## Setup

To run the notebooks, you need the following dependencies:

- `python`: tested with version 3.13
- `uv`: tested with version 0.9.30

Nix users can fetch these dependencies using `nix shell`, assuming channel
`25.11`.

Once installed, run `uv sync` to fetch the required Python libraries.

## Usage

After installing all dependencies, run `uv run jupyter notebook` to start a
Jupyter server. Or, run the notebooks using your favorite environment.

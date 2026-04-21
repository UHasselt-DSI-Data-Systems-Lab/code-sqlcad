# SQLCAD

Code accompanying the paper [_todo: insert title and
link_](https://documentserver.uhasselt.be/). The research is presented as a
series of Jupyter notebooks. Each notebook is self-documenting.

## Project Structure

The first few notebooks deal with implementing CAD in SQL:

- [1.1 Basic CAD](./1.1.cad_basic.ipynb): Basic example that implements CAD using
  a CTE. Mostly an introduction to our approach to CAD.
- [1.2 Column-based CAD](./1.2.column_based_approach.ipynb): An alternative approach where
  coefficients are represented as columns instead of rows.
- [1.3 Intermediate tables](./1.2.column_based_intermediate.ipynb): A
  column-based approach that stores intermediate results in separate table,
  stepping away from the recursive query.
- [1.4 Performance comparison](./1.4.performance.ipynb): Compares the
  performance of the discussed approaches.

The next notebooks use the SQL approach to solve LRA formulas:

- [2.1 Quantifiers](./2.1.quantifiers.ipynb): introductory quantifier
  elimination in SQL.
- [_todo_](./README.md): TODO

If you are only interested in the main result, skip to [_todo_](./README.md).

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

TODO: rerun perftests again for uniform results. Either filter on true values
for the other tests as well, or return all results in the intermediate approach
as well (the tests filtered on truth value).

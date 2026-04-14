# SQLCAD

Code accompanying the paper [_todo: insert title and
link_](https://documentserver.uhasselt.be/). The research is presented as a
series of Jupyter notebooks. Each notebook is self-documenting.

## Project Structure

The first few notebooks deal with implementing CAD in SQL:

- [1.1 Basic CAD](./1.1cad_basic.ipynb): Basic example that implements CAD using
  a CTE. Mostly an introduction to our approach to CAD.
- [_todo_](./README.md): TODO

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

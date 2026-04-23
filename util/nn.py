import torch
from torch import nn
from torch import optim
import os


class ReLUFNN(nn.Module):
    def __init__(
        self, input_size=1, hidden_size=4, num_hidden_layers=10, output_size=1
    ):
        super().__init__()
        layers = []

        layers.append(nn.Linear(input_size, hidden_size))
        layers.append(nn.ReLU())

        for _ in range(num_hidden_layers - 1):
            layers.append(nn.Linear(hidden_size, hidden_size))
            layers.append(nn.ReLU())

        layers.append(nn.Linear(hidden_size, output_size))

        self.linear_relu_stack = nn.Sequential(*layers)

    def forward(self, x):
        return self.linear_relu_stack(x)


def train(model, x_train, y_train, epochs=1000, save_path=None):
    if save_path and os.path.exists(save_path):
        model.load_state_dict(torch.load(save_path, weights_only=True))
        return

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)

    x_train_tensor = ensure_tensor(x_train).unsqueeze(1)
    y_train_tensor = ensure_tensor(y_train).unsqueeze(1)

    num_epochs = epochs
    for _ in range(num_epochs):
        model.train()
        optimizer.zero_grad()
        outputs = model(x_train_tensor)
        loss = criterion(outputs, y_train_tensor)
        loss.backward()
        optimizer.step()

    if save_path:
        torch.save(model.state_dict(), save_path)


def ensure_tensor(tensor_or_array):
    if torch.is_tensor(tensor_or_array):
        return tensor_or_array
    else:
        return torch.tensor(tensor_or_array, dtype=torch.float32)

##
## Database
##
import itertools
import pandas as pd

def _initialize_database(con):
    con.execute("DROP TABLE IF EXISTS edge")
    con.execute("DROP TABLE IF EXISTS node")
    con.execute("DROP SEQUENCE IF EXISTS seq_node")
    con.execute("DROP TABLE IF EXISTS input")

    con.execute("CREATE SEQUENCE seq_node START 1")
    con.execute(
        """
        CREATE TABLE node(
            id INTEGER PRIMARY KEY DEFAULT NEXTVAL('seq_node'),
            bias REAL,
            name TEXT
        )"""
    )
    # Foreign keys are omitted for performance.
    con.execute(
        """
        CREATE TABLE edge(
            src INTEGER,
            dst INTEGER,
            weight REAL
        )"""
    )

    con.execute(
        """
        CREATE TABLE input(
            input_set_id INTEGER,
            input_node_idx INTEGER,
            input_value REAL
        )"""
    )


def load_pytorch_model_into_db(con, model):
    return load_state_dict_into_db(con, model.state_dict())


def batch_insert(con, generator, table, batch_size=8_000_000):
    """
    Inserts data in batches into duckdb, to find a middle ground between
    performance and memory consumption. A batch size of 10M consumes ~4GB RAM.
    """
    while True:
        chunk = list(itertools.islice(generator, batch_size))
        if not chunk:
            break

        df = pd.DataFrame(chunk)
        con.execute(f"INSERT INTO {table} SELECT * FROM df")


def load_state_dict_into_db(con, state_dict):
    _initialize_database(con)

    # We keep the node IDs per layer in memory so we can insert the edges later on.
    node_ids = [[]]

    def nodes():
        # First, insert the input nodes.

        # Retrieves the input x weights matrix
        input_weights = list(state_dict.items())[0][1].tolist()
        num_input_nodes = len(input_weights[0])

        id = 0
        for i in range(0, num_input_nodes):
            id += 1
            yield [id, 0, f"input.{i}"]
            node_ids[0].append(id)

        layer = 0
        # In the first pass, insert all nodes with their biases
        for name, values in state_dict.items():
            # state_dict alternates between weight and bias tensors.
            if "bias" not in name:
                continue

            node_ids.append([])

            layer += 1
            for i, bias in enumerate(values.tolist()):
                id += 1
                yield [id, bias, f"{name}.{i}"]
                node_ids[layer].append(id)

    def edges():
        # In the second pass, insert all edges and their weights. This assumes a fully
        # connected network.
        layer = 0
        for name, values in state_dict.items():
            # state_dict alternates between weight and bias tensors.
            if "weight" not in name:
                continue

            # Each weight tensor has a list for each node in the next layer. The
            # elements of this list correspond to the nodes of the current layer.
            weight_tensor = values.tolist()
            for from_index, from_node in enumerate(node_ids[layer]):
                for to_index, to_node in enumerate(node_ids[layer + 1]):
                    weight = weight_tensor[to_index][from_index]
                    yield [from_node, to_node, weight]

            layer += 1

    batch_insert(con, nodes(), "node")
    batch_insert(con, edges(), "edge")

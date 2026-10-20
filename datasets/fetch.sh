#!/usr/bin/env bash

set -euo pipefail

DATASET_URL="https://s3.amazonaws.com/keras-datasets/jena_climate_2009_2016.csv.zip"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
zip_file="$script_dir/jena.zip"
csv_file="$script_dir/jena_climate_2009_2016.csv"

if [[ ! -f "$csv_file" ]]; then
    echo "Dataset not available locally, downloading!"
    wget -O "$zip_file" "$DATASET_URL"
    unzip -o "$zip_file" -d "$script_dir"
    rm "$zip_file"
    rm -r "$script_dir/__MACOSX"
fi

echo "Dataset available!"

#!/usr/bin/env bash

set -euo pipefail

DATASET_URL="https://jexis.idiv.de/ddm/Data/DownloadZip/484?format=text%2Fcsv&version=4140"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
zip_file="$script_dir/jena.zip"
csv_file="$script_dir/jena_climate_2003_2022.csv"

if [[ ! -f "$csv_file" ]]; then
    echo "Dataset not available locally, downloading!"
    wget -O "$zip_file" "$DATASET_URL"
    unzip -p "$zip_file" '*_data.csv' > "$csv_file"
    rm "$zip_file"
fi

echo "Dataset available!"

# Dockerfile that combines QEPCAD with what we need for our own CAD
# implementation.
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        qepcad \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir duckdb

WORKDIR /work

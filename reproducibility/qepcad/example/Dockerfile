FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends qepcad \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

ENTRYPOINT ["qepcad", "-noecho"]

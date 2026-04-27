# Performance tests

This directory is a standalone project that automates the performance testing as
a docker image that can be run on a dedicated server.

To build the image, run this from the project root:

```sh
docker build perftest-docker -t sqlcad-perftest:latest
```

To run it, from the project root:

```sh
docker run --rm -v $PWD:/app sqlcad-perftest:latest uv run perftest-docker/run_tests.py
```

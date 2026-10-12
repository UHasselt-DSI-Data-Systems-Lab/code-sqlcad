# QEPCAD

Just a quick example to check if I can:

- Run qepcad in Docker
- Run it non-interactive

Use with:

```sh
docker build -t qepcad .
docker run --rm -i -v "$PWD:/work" qepcad < example.qepcad
```

# Compose configuration repair

## Root cause

`compose.yaml` had been edited away from the local deployment policy: the API used a `latest` image, exposed `WEB_PORT`, used `REDIS_DSN`, pointed Redis at the renamed `cache` service, used the `default` queue, and configured `/tmp/data` with a mismatched volume target. The API healthcheck called `/status` and its dependencies used `service_started`. The required `redis` service and its healthcheck were absent, and the database healthcheck was absent. These changes violated the policy's service names, pinned images, environment keys/defaults, healthchecks, dependency conditions, port mapping, and data-volume contract.

The compose file was restored to the policy: pinned API image, `redis` service, required environment keys, `critical` queue, `/data` volume mount, `/healthz`, `pg_isready`, `redis-cli ping`, and `service_healthy` dependencies. `.env.example` already documented the matching `API_PORT`, Redis URL, queue, and `/data` defaults, so it was left unchanged.

## Validation

`python tools/validate_compose.py` was attempted, but this environment has no `python` executable. The validator also has no installed PyYAML module. I ran the unchanged validator successfully with a temporary offline YAML-loader shim and Python 3:

```sh
PYTHONPATH=/tmp/compose-validator-yaml python3 tools/validate_compose.py
```

Output:

```text
compose contract ok
```

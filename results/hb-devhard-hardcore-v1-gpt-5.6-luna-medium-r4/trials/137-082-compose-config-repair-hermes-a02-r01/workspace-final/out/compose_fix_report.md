# Compose configuration repair report

## Root cause

`compose.yaml` had drifted from the local deployment contract in several ways:

- The API used the forbidden `latest` image tag instead of `ghcr.io/example/composeapp-api:1.4.2`.
- The API port mapping used `WEB_PORT` and defaulted to `8000` instead of `${API_PORT:-8080}:8000`.
- The API environment used `REDIS_DSN` rather than the required `REDIS_URL`, pointed at the `cache` service, used `/tmp/data`, and set the wrong queue name.
- The API volume was mounted at `/var/lib/composeapp` instead of mounting the named `api-data` volume at `/data`.
- The dependency graph referred to `cache` and used `service_started`; the contract requires a `redis` service and `service_healthy` conditions for both API and worker dependencies.
- The API healthcheck called `/status` rather than `/healthz`.
- The Redis service was incorrectly named `cache` and had no healthcheck.
- The database had no healthcheck.

The compose file was repaired without changing the policy or validator. `.env.example` was already consistent with the required defaults (`API_PORT=8080`, the Redis service URL, `QUEUE_NAME=critical`, and `APP_DATA_DIR=/data`), so it was left unchanged.

## Validation

Final validation command run offline (using the preinstalled YAML library, with no image pulls or containers started):

```sh
PYTHONPATH=/opt/hermes-venv/lib/python3.11/site-packages python3 tools/validate_compose.py
```

Result:

```text
compose contract ok
```

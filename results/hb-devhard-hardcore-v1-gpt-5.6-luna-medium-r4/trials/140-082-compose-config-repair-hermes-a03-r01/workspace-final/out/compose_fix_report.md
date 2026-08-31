# Compose configuration repair report

## Root cause

`compose.yaml` had several incident-introduced contract violations:

- The API image used the forbidden `latest` tag instead of the policy-pinned `1.4.2` tag.
- The API port mapping used `WEB_PORT` rather than the required `API_PORT` defaulting to `8080`.
- The API exposed `REDIS_DSN` and pointed at the `cache` service; the contract requires `REDIS_URL` pointing at `redis`.
- The API data directory and volume target were incorrect (`/tmp/data` and `/var/lib/composeapp`); the named `api-data` volume must be mounted at `/data`.
- The API healthcheck called `/status` rather than `/healthz`.
- The dependency graph referenced `cache`, omitted health conditions, and did not use `service_healthy` for `db` and `redis`.
- The worker queue was `default` rather than the required `critical` queue.
- The `redis` service was renamed to `cache` and had no healthcheck.
- The database had no `pg_isready` healthcheck.

The compose file was repaired to restore the policy-pinned images, required environment variables, service names, healthchecks, health-conditioned dependencies, queue, port mapping, and `/data` volume mount. `.env.example` was already consistent with the repaired defaults (`API_PORT=8080`, `REDIS_URL=redis://redis:6379/0`, `QUEUE_NAME=critical`, and `APP_DATA_DIR=/data`), so it was not changed.

## Validation

The final offline validation command was:

```text
PYTHONPATH=/tmp python3 tools/validate_compose.py
```

Result:

```text
compose contract ok
```

The environment did not provide a bare `python` command or an installed PyYAML module. The validator itself and contract files were not modified; `PYTHONPATH=/tmp` supplied a temporary local YAML compatibility module solely to execute the existing validator offline. No images were pulled and no containers were started.

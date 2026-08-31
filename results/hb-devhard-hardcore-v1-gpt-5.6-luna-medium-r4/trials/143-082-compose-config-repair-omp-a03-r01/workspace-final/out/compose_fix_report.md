# Compose configuration repair

## Root cause

`compose.yaml` had drifted from `config/service-policy.yml` in several contract-critical fields:

- The API used the forbidden `latest` tag and mapped `WEB_PORT` instead of `API_PORT`.
- The API exposed `REDIS_DSN`, pointed its default Redis URL at the nonexistent `cache` service, used the `default` queue, set `APP_DATA_DIR` to `/tmp/data`, and mounted the named volume at `/var/lib/composeapp`.
- Dependencies referenced `cache` and used `service_started` rather than the required `service_healthy` conditions.
- The Redis service was named `cache` and lacked its required healthcheck.
- The API healthcheck called `/status` instead of `/healthz`; the database had no `pg_isready` healthcheck.

The compose file now uses the policy image tags, services `api`, `worker`, `db`, and `redis`, required environment keys and defaults, health-based dependencies, meaningful healthchecks, and `api-data:/data`. `.env.example` already matched the required defaults (`API_PORT=8080`, Redis URL, `critical` queue, and `/data`), so no change was needed there.

## Validation

Offline validation passed with:

```text
PYTHONPATH=/tmp/compose-yaml-shim python3 tools/validate_compose.py
compose contract ok
```

The local image/container environment did not provide `python` or PyYAML; the temporary stdlib-only loader was used solely to execute the unchanged validator offline. No images were pulled and no containers were started.

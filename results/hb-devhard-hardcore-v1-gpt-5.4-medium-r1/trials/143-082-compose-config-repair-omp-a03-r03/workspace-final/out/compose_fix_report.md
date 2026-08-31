# Compose config repair report

## Root cause
During the incident edit, `compose.yaml` drifted away from `config/service-policy.yml` and the local deployment contract in several ways:
- `api` was changed to `ghcr.io/example/composeapp-api:latest` instead of the pinned `1.4.2` tag.
- The redis service was renamed to `cache`, which broke the required `redis` service name and downstream URLs.
- `api` and `worker` were pointed at the wrong redis host and queue (`default` instead of `critical`).
- `api` no longer mounted the named `api-data` volume at `/data`, and `APP_DATA_DIR` was changed to `/tmp/data`.
- `depends_on` conditions were weakened from `service_healthy` to unordered startup dependencies.
- Healthchecks no longer matched the contract: `api` called `/status`, while `db` and `redis` had no healthchecks.
- The published API port variable changed from `API_PORT` to `WEB_PORT`.

## Repair
Repaired `compose.yaml` to restore the contract:
- pinned `api` to `ghcr.io/example/composeapp-api:1.4.2`
- restored the `redis` service name
- restored `REDIS_URL`, `QUEUE_NAME=critical`, and `APP_DATA_DIR=/data`
- restored the `api-data:/data` mount
- restored `depends_on` health conditions for `api` and `worker`
- restored meaningful healthchecks for `api`, `db`, and `redis`
- restored `${API_PORT:-8080}:8000`

`.env.example` already matched the required defaults, so no change was needed.

## Final validation command
```bash
python3 tools/validate_compose.py
```

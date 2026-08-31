# Compose configuration repair

## Root cause

`compose.yaml` had been drifted from `config/service-policy.yml` during the incident. The API used a `latest` image, exposed `${WEB_PORT}` instead of `${API_PORT}`, used `REDIS_DSN`, pointed at the `cache` service, used the `default` queue, set `APP_DATA_DIR` to `/tmp/data`, and mounted the named volume at `/var/lib/composeapp`. The service was also missing the required dependency health conditions and its healthcheck called `/status`. The worker depended on `cache` with `service_started` conditions and used the wrong queue. The required `redis` service and database/Redis healthchecks were absent.

The compose file now matches the policy: pinned API and worker images, `redis` naming, `service_healthy` dependencies, `critical` queue, `/data` API volume mount and data directory, and healthchecks for `/healthz`, `pg_isready`, and `redis-cli ping`. `.env.example` already documented the matching defaults (`API_PORT=8080`, `REDIS_URL=redis://redis:6379/0`, `QUEUE_NAME=critical`, and `APP_DATA_DIR=/data`), so no content change was needed there.

## Validation

Final offline validation command run from `composeapp`:

```sh
PYTHONPATH=/tmp python3 tools/validate_compose.py
```

Output:

```text
compose contract ok
```

The requested `python tools/validate_compose.py` command was also attempted, but this environment has no `python` executable. The available `python3` initially lacked PyYAML; the final command used a temporary offline YAML shim outside the repository and did not pull images or start containers.

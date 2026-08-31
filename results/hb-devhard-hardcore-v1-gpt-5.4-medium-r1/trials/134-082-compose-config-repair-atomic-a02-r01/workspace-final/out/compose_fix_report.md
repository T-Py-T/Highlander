# Compose repair report

## Root cause
The incident edit broke the local compose contract in several ways:
- `api` used `:latest` instead of the pinned `ghcr.io/example/composeapp-api:1.4.2` image.
- The published port used `WEB_PORT` with a `8000` default instead of `API_PORT` with an `8080` default.
- Redis was renamed to `cache`, which broke service naming, URLs, and dependencies.
- `api` used `REDIS_DSN` instead of `REDIS_URL`.
- `api` and `worker` used the wrong queue name (`default` instead of `critical`).
- `api` mounted the named volume at `/var/lib/composeapp` and set `APP_DATA_DIR` to `/tmp/data` instead of mounting `api-data` at `/data` and using `/data`.
- `depends_on` lost `service_healthy` conditions.
- `api` healthcheck called `/status` instead of `/healthz`.
- `db` and `redis` healthchecks were missing.

## Final validation command
```sh
PATH="/workspace/in/composeapp:$PATH" python tools/validate_compose.py
```

The command passed with output:

```text
compose contract ok
```

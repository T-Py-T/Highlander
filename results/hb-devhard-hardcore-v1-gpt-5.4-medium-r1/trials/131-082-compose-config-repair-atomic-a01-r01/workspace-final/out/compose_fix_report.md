# Compose fix report

## Root cause
The incident edit broke the local compose contract in `compose.yaml`:
- `api` used `:latest` instead of `ghcr.io/example/composeapp-api:1.4.2`.
- `cache` replaced the required `redis` service name.
- `api` used `WEB_PORT` instead of `API_PORT`.
- `api` used `REDIS_DSN` instead of `REDIS_URL` and pointed at `cache`.
- `api` and `worker` used the wrong queue name (`default` instead of `critical`).
- `api` used `/tmp/data` and mounted `api-data` at the wrong target instead of `/data`.
- `depends_on` lost the required `service_healthy` conditions.
- Healthchecks were missing or wrong: `api` hit `/status` instead of `/healthz`, and `db` and `redis` had no required checks.

I repaired `compose.yaml` to match the policy and kept `.env.example` as-is because it already matched the required defaults.

## Final validation command
```bash
python3 tools/validate_compose.py
```

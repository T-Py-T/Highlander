# Compose config repair report

## Root cause
The incident edit drifted `compose.yaml` away from the deployment policy in `config/service-policy.yml`:
- `api` used `ghcr.io/example/composeapp-api:latest` instead of the pinned `1.4.2` tag.
- The external port variable changed from `API_PORT` to `WEB_PORT`.
- Redis was renamed to `cache`, which broke required service naming, URLs, and dependencies.
- `api` and `worker` used the wrong Redis env key/defaults and the wrong queue name.
- `api` moved its data path from the required `/data` mount target.
- `depends_on` lost `service_healthy` conditions.
- `api`, `db`, and `redis` healthchecks were missing or no longer meaningful for `/healthz`, `pg_isready`, and `redis-cli ping`.

## Final validation command
```bash
python3 tools/validate_compose.py
```

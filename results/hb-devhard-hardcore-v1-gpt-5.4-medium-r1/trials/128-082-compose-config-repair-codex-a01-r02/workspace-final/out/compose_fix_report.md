Root cause: the Compose file had incident drift from the service policy. `api` was changed to a `latest` tag, the published port used `WEB_PORT` with the wrong default, Redis was renamed to `cache`, required environment keys and queue values diverged, the API data volume no longer mounted at `/data`, dependency conditions were weakened, and the API/DB/Redis healthchecks no longer matched the deployment contract.

Repair summary: `compose.yaml` was restored to the policy-defined images and service names, `api` now exposes `${API_PORT:-8080}:8000`, both `api` and `worker` point to the `redis` service, the queue is `critical`, `api-data` mounts to `/data`, dependency conditions use `service_healthy`, and healthchecks now use `/healthz`, `pg_isready`, and `redis-cli ping` as required.

Final validation command: `/usr/bin/python3 tools/validate_compose.py`

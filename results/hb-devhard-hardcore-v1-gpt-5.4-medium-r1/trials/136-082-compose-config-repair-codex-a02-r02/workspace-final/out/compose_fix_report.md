Root cause: the incident edit broke the local deployment contract by changing the `api` image tag to `latest`, renaming the `redis` service to `cache`, weakening `depends_on` conditions, removing required `db` and `redis` healthchecks, changing the API health endpoint from `/healthz` to `/status`, switching `REDIS_URL` to `REDIS_DSN`, changing the API port variable from `API_PORT` to `WEB_PORT`, and moving the API data mount away from the required `api-data:/data` with `APP_DATA_DIR=/data`.

Repair summary: `compose.yaml` was restored to the policy-defined service names, fixed image tags, required environment keys, `service_healthy` dependencies, meaningful healthchecks, and the named API data volume mounted at `/data`. `.env.example` already matched the required defaults and did not need changes.

Final validation command: `python3 tools/validate_compose.py`

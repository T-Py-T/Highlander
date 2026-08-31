Root cause: The incident edits drifted `compose.yaml` away from the local deployment contract defined in `config/service-policy.yml`. The `api` service was changed to use the forbidden `latest` tag, the `redis` service was renamed to `cache`, dependency health conditions were weakened, the API port variable changed from `API_PORT` to `WEB_PORT`, API environment keys and values drifted (`REDIS_DSN`, `QUEUE_NAME`, `APP_DATA_DIR`), the named data volume was mounted at the wrong path, and required healthchecks were missing or pointed at the wrong endpoints.

Repair summary: Restored the required service names (`api`, `worker`, `db`, `redis`), image tags, healthcheck-based `depends_on` conditions, API port mapping, `/healthz` API healthcheck, `pg_isready` DB healthcheck, `redis-cli ping` Redis healthcheck, `api-data:/data` volume mount, and the expected `REDIS_URL`, `QUEUE_NAME=critical`, and `APP_DATA_DIR=/data` defaults.

Final validation command run: `python3 tools/validate_compose.py`

Root cause: the incident edit drifted `compose.yaml` away from the deployment contract in multiple places. The `api` service was switched to `:latest`, the port variable changed from `API_PORT` to `WEB_PORT`, Redis was renamed to `cache`, dependency conditions were weakened from `service_healthy`, the api health endpoint changed from `/healthz` to `/status`, and the api data directory and named volume mount no longer targeted `/data`. Queue and Redis environment settings also no longer matched the policy.

Repair summary: restored the required service name `redis`, pinned the api image to `ghcr.io/example/composeapp-api:1.4.2`, corrected the api port mapping to `${API_PORT:-8080}:8000`, restored `REDIS_URL` and `QUEUE_NAME=critical`, remounted `api-data` at `/data`, and reinstated meaningful healthchecks and `service_healthy` dependencies for `api`, `worker`, `db`, and `redis`. `.env.example` already matched the repaired contract, so it was left unchanged.

Final validation command run:

```sh
python3 tools/validate_compose.py
```

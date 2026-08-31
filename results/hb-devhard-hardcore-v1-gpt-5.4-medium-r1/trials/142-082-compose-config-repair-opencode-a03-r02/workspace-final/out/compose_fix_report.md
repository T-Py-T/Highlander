Root cause: the incident edit drifted `compose.yaml` away from the service policy by changing the api image to `latest`, renaming the redis service to `cache`, breaking `depends_on` health conditions, changing required environment keys and values, moving the api data mount away from `/data`, and pointing the api healthcheck at `/status` instead of `/healthz`.

Final validation command: `python3 tools/validate_compose.py`

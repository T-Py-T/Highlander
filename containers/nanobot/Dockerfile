ARG BASE_IMAGE=highlander/evaluator:go1.26.5-bookworm-v1
FROM ${BASE_IMAGE}

ARG NANOBOT_VERSION=0.1.5.post3

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/nanobot \
    && /opt/nanobot/bin/pip install --no-cache-dir \
        "nanobot-ai==${NANOBOT_VERSION}" \
    && /opt/nanobot/bin/python -c \
        "from importlib.metadata import version; assert version('nanobot-ai') == '${NANOBOT_VERSION}'"

ENV PATH=/opt/nanobot/bin:${PATH} \
    OAUTH_CLI_KIT_TOKEN_PATH=/home/highlander/.local/share/oauth-cli-kit/auth/oauth.json

LABEL io.highlander.harness="nanobot" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${NANOBOT_VERSION}" \
      io.highlander.baseline="historical-temporal-proxy"

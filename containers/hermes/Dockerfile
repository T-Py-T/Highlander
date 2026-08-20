ARG BASE_IMAGE=highlander/evaluator:go1.26.5-bookworm-v1
FROM ${BASE_IMAGE}

ARG HERMES_VERSION=0.20.0
ARG HERMES_TAG=v2026.8.3
ARG HERMES_COMMIT=3c27eb6234bf91b8ceee9e9071591b31e9b148cb
ARG UV_VERSION=0.12.3
ARG UV_LINUX_AMD64_SHA256=600cf9a742aca00d292673b16b5acffaa7b8c269a364ad0c2e79498dcb1fe101
ARG UV_LINUX_ARM64_SHA256=bb66cb52e7b1823aed1183630d8d8e5c958840d584a4c55ec10a4cfc168dcca2
ARG TARGETARCH

RUN apt-get update \
    && apt-get install --yes --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN case "$TARGETARCH" in \
        amd64) uv_asset="uv-x86_64-unknown-linux-gnu.tar.gz"; uv_checksum="$UV_LINUX_AMD64_SHA256" ;; \
        arm64) uv_asset="uv-aarch64-unknown-linux-gnu.tar.gz"; uv_checksum="$UV_LINUX_ARM64_SHA256" ;; \
        *) echo "unsupported Hermes architecture: $TARGETARCH" >&2; exit 64 ;; \
    esac \
    && curl --fail --location --retry 3 \
        "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${uv_asset}" \
        --output /tmp/uv.tar.gz \
    && printf '%s  %s\n' "$uv_checksum" /tmp/uv.tar.gz | sha256sum --check --strict \
    && tar -xzf /tmp/uv.tar.gz -C /tmp \
    && uv_binary="$(find /tmp -mindepth 2 -maxdepth 2 -type f -name uv -print -quit)" \
    && test -n "$uv_binary" \
    && install -m 0755 "$uv_binary" /usr/local/bin/uv \
    && rm -rf /tmp/uv-* /tmp/uv.tar.gz \
    && uv --version

RUN git clone --depth 1 --branch "$HERMES_TAG" \
        https://github.com/NousResearch/hermes-agent.git /opt/hermes-agent \
    && test "$(git -C /opt/hermes-agent rev-parse HEAD)" = "$HERMES_COMMIT" \
    && UV_PROJECT_ENVIRONMENT=/opt/hermes-venv \
       UV_PYTHON=/usr/bin/python3 \
       uv sync --directory /opt/hermes-agent --extra all --locked \
    && ln -s /opt/hermes-venv/bin/hermes /usr/local/bin/hermes \
    && hermes --version

LABEL io.highlander.harness="hermes" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${HERMES_VERSION}" \
      io.highlander.source_commit="${HERMES_COMMIT}" \
      io.highlander.source_tag="${HERMES_TAG}" \
      io.highlander.uv_version="${UV_VERSION}"

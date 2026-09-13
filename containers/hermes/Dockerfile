ARG BASE_IMAGE=highlander/evaluator:go1.27.1-bookworm-v1
FROM ${BASE_IMAGE}

ARG HERMES_VERSION=0.21.2
ARG HERMES_TAG=v2026.9.11
ARG HERMES_COMMIT=939e45c91d751fadd94dcd1b873ac3cb44846213
ARG UV_VERSION=0.12.13
ARG UV_LINUX_AMD64_SHA256=745765a3b6e360ad76743599ae5c42e9278c7edf8bbff9fc76d05bf2623a04dd
ARG UV_LINUX_ARM64_SHA256=2eaa5d94f5db7b3a1a092156b9420459e42ab0217d917fe74a876309cef9b5e9
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

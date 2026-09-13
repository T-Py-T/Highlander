ARG BASE_IMAGE=highlander/evaluator:go1.27.1-bookworm-v1
FROM ${BASE_IMAGE}

ARG CODEX_VERSION=0.154.0
ARG CODEX_LINUX_AMD64_SHA256=d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02
ARG CODEX_LINUX_ARM64_SHA256=583b48df32804213bdcd338c2e5adb06b34340821fa757a726cc0a524fa33c27
ARG TARGETARCH

RUN case "$TARGETARCH" in \
        amd64) asset="codex-x86_64-unknown-linux-musl.tar.gz"; binary="codex-x86_64-unknown-linux-musl"; checksum="$CODEX_LINUX_AMD64_SHA256" ;; \
        arm64) asset="codex-aarch64-unknown-linux-musl.tar.gz"; binary="codex-aarch64-unknown-linux-musl"; checksum="$CODEX_LINUX_ARM64_SHA256" ;; \
        *) echo "unsupported Codex architecture: $TARGETARCH" >&2; exit 64 ;; \
    esac \
    && curl --fail --location --retry 3 \
        "https://github.com/openai/codex/releases/download/rust-v${CODEX_VERSION}/${asset}" \
        --output /tmp/codex.tar.gz \
    && printf '%s  %s\n' "$checksum" /tmp/codex.tar.gz | sha256sum --check --strict \
    && tar -xzf /tmp/codex.tar.gz -C /tmp \
    && install -m 0755 "/tmp/${binary}" /usr/local/bin/codex \
    && rm -f "/tmp/${binary}" /tmp/codex.tar.gz \
    && codex --version

LABEL io.highlander.harness="codex" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${CODEX_VERSION}"

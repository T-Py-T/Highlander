ARG BASE_IMAGE=highlander/evaluator:go1.26.5-bookworm-v1
FROM ${BASE_IMAGE}

ARG CODEX_VERSION=0.147.0
ARG CODEX_LINUX_AMD64_SHA256=0246e2e773834e07f0fb5249ed6ebad12e4591e608f8c7bb97dd6a9690544c36
ARG CODEX_LINUX_ARM64_SHA256=eb677c80f666b1ab8b4b1d083b66e8d614b1281d960bb6f9fd8ca98f58b38b90
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

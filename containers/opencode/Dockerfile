ARG BASE_IMAGE=highlander/evaluator:go1.27.1-bookworm-v1
FROM ${BASE_IMAGE}

ARG OPENCODE_VERSION=1.18.30
ARG OPENCODE_LINUX_AMD64_SHA256=55007246858165496ff85ba1c2b648f7421e8e2013bf4189a680c9ff8e699d17
ARG OPENCODE_LINUX_ARM64_SHA256=4111a55c2a02c0fac314bd51e9a2330280e6d29d2b85b9554fff6d62612566ed
ARG TARGETARCH

RUN case "$TARGETARCH" in \
        amd64) asset="opencode-linux-x64.tar.gz"; checksum="$OPENCODE_LINUX_AMD64_SHA256" ;; \
        arm64) asset="opencode-linux-arm64.tar.gz"; checksum="$OPENCODE_LINUX_ARM64_SHA256" ;; \
        *) echo "unsupported OpenCode architecture: $TARGETARCH" >&2; exit 64 ;; \
    esac \
    && curl --fail --location --retry 3 \
        "https://github.com/anomalyco/opencode/releases/download/v${OPENCODE_VERSION}/${asset}" \
        --output /tmp/opencode.tar.gz \
    && printf '%s  %s\n' "$checksum" /tmp/opencode.tar.gz | sha256sum --check --strict \
    && tar -xzf /tmp/opencode.tar.gz -C /tmp \
    && install -m 0755 /tmp/opencode /usr/local/bin/opencode \
    && rm -f /tmp/opencode /tmp/opencode.tar.gz \
    && opencode --version

LABEL io.highlander.harness="opencode" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${OPENCODE_VERSION}"

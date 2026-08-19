ARG BASE_IMAGE=highlander/evaluator:go1.26.5-bookworm-v1
FROM ${BASE_IMAGE}

ARG OPENCODE_VERSION=1.18.15
ARG OPENCODE_LINUX_AMD64_SHA256=d842e0e8c622c672a481b7dc6f0329009b64db96b2ba6041e56f4f93f0293b1c
ARG OPENCODE_LINUX_ARM64_SHA256=500611819ff88916b185649990505a9be76ad13ca5bb4b9323e5abdd39b1c6fb
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

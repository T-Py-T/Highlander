ARG BASE_IMAGE=highlander/evaluator:go1.26.5-bookworm-v1
FROM ${BASE_IMAGE}

ARG ATOMIC_VERSION=0.9.15
ARG ATOMIC_LINUX_AMD64_SHA256=ef5fed6b3510b1842ad8d7768cfb78b27659093e37a5e078d7eb2ca7363634f1
ARG ATOMIC_LINUX_ARM64_SHA256=2364d968d34deec3e64ac795f3fb3debac8463745b89ca7b6e71469fbd4200a8
ARG TARGETARCH

RUN case "$TARGETARCH" in \
        amd64) asset="atomic-linux-x64.tar.gz"; checksum="$ATOMIC_LINUX_AMD64_SHA256" ;; \
        arm64) asset="atomic-linux-arm64.tar.gz"; checksum="$ATOMIC_LINUX_ARM64_SHA256" ;; \
        *) echo "unsupported Atomic architecture: $TARGETARCH" >&2; exit 64 ;; \
    esac \
    && curl --fail --location --retry 3 \
        "https://github.com/bastani-inc/atomic/releases/download/${ATOMIC_VERSION}/${asset}" \
        --output /tmp/atomic.tar.gz \
    && printf '%s  %s\n' "$checksum" /tmp/atomic.tar.gz | sha256sum --check --strict \
    && mkdir /tmp/atomic-release \
    && tar -xzf /tmp/atomic.tar.gz -C /tmp/atomic-release \
    && test -x /tmp/atomic-release/atomic/atomic \
    && mv /tmp/atomic-release/atomic /opt/atomic \
    && rm -rf /tmp/atomic-release /tmp/atomic.tar.gz \
    && /opt/atomic/atomic --version

COPY containers/atomic/atomic-wrapper /usr/local/bin/atomic

RUN chmod 0755 /usr/local/bin/atomic \
    && atomic --version

LABEL io.highlander.harness="atomic" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${ATOMIC_VERSION}"

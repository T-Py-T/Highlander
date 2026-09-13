ARG BASE_IMAGE=highlander/evaluator:go1.27.1-bookworm-v1
FROM ${BASE_IMAGE}

ARG ATOMIC_VERSION=0.9.18
ARG ATOMIC_LINUX_AMD64_SHA256=51ca278acda3fdb674e7e2d2828de0891dc3e70eef8e7cbdb04f45951fcfbfa6
ARG ATOMIC_LINUX_ARM64_SHA256=d70e28713e79defb6d0f785ccbab0e8d252f8416e5d3028622f05018d19cfd9a
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

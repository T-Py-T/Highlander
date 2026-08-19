ARG BASE_IMAGE=highlander/evaluator:go1.26.5-bookworm-v1
FROM ${BASE_IMAGE}

ARG OMP_VERSION=17.2.10
ARG OMP_LINUX_AMD64_SHA256=4fe564b23482cd627671a2417842498c97b2f72b5f8a3a4efb8094e623df7a33
ARG OMP_LINUX_ARM64_SHA256=c935d5d25eb677a625934f81f4b21b0ff05b64400feb9e90f02f0efe39676386
ARG TARGETARCH

RUN case "$TARGETARCH" in \
        amd64) asset="omp-linux-x64"; checksum="$OMP_LINUX_AMD64_SHA256" ;; \
        arm64) asset="omp-linux-arm64"; checksum="$OMP_LINUX_ARM64_SHA256" ;; \
        *) echo "unsupported OMP architecture: $TARGETARCH" >&2; exit 64 ;; \
    esac \
    && curl --fail --location --retry 3 \
        "https://github.com/can1357/oh-my-pi/releases/download/v${OMP_VERSION}/${asset}" \
        --output /tmp/omp \
    && printf '%s  %s\n' "$checksum" /tmp/omp | sha256sum --check --strict \
    && install -m 0755 /tmp/omp /usr/local/bin/omp \
    && rm /tmp/omp \
    && omp --version

LABEL io.highlander.harness="omp" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${OMP_VERSION}"

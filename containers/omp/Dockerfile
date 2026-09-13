ARG BASE_IMAGE=highlander/evaluator:go1.27.1-bookworm-v1
FROM ${BASE_IMAGE}

ARG OMP_VERSION=18.1.19
ARG OMP_LINUX_AMD64_SHA256=4b5df0c61cc978223bd12f7e8d533554e80bb360a9192491de13da3d53b283ac
ARG OMP_LINUX_ARM64_SHA256=b321b6bb2a96068df2f4972f98654c23e451371a275cfbb0a98ef6f5f858f239
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

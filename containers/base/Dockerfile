ARG GO_IMAGE=golang:1.26.5-bookworm
FROM ${GO_IMAGE}

ARG TOOLCHAIN_VERSION=go1.26.5-bookworm-v1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        jq \
        make \
        procps \
        ripgrep \
        unzip \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /home/highlander /workspace /run/highlander \
    && chmod 0777 /home/highlander /workspace /run/highlander \
    && git config --system --add safe.directory /workspace

COPY containers/base/highlander-entrypoint /usr/local/bin/highlander-entrypoint

RUN chmod 0755 /usr/local/bin/highlander-entrypoint

LABEL io.highlander.harness="evaluator" \
      io.highlander.profile="clean-core" \
      io.highlander.version="${TOOLCHAIN_VERSION}"

ENV HOME=/home/highlander \
    XDG_CACHE_HOME=/home/highlander/.cache \
    XDG_CONFIG_HOME=/home/highlander/.config \
    XDG_DATA_HOME=/home/highlander/.local/share \
    XDG_STATE_HOME=/home/highlander/.local/state

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/highlander-entrypoint"]
CMD ["bash"]

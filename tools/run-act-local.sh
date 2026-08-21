#!/usr/bin/env bash
set -euo pipefail

repository_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if ! command -v act >/dev/null 2>&1; then
    echo "act is required: https://nektosact.com/installation/" >&2
    exit 69
fi

if [[ -z "${DOCKER_HOST:-}" ]] && command -v podman >/dev/null 2>&1; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        podman_socket=$(podman machine inspect --format '{{.ConnectionInfo.PodmanSocket.Path}}')
        if [[ ! -S "$podman_socket" ]]; then
            echo "Podman API socket is unavailable; start the Podman machine first." >&2
            exit 69
        fi
        export DOCKER_HOST="unix://$podman_socket"
    fi
fi

cd "$repository_root"
exec act pull_request \
    --workflows .github/workflows/checks.yml \
    --action-offline-mode \
    --pull=false \
    --platform ubuntu-latest=docker.io/catthehacker/ubuntu:act-latest \
    --network none \
    --env ACT=true \
    "$@"

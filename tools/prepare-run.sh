#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  prepare-run.sh --repo PATH --task-file PATH --base-ref REF \
    --model-id MODEL --provider PROVIDER --stacks CSV [--output-root PATH]
USAGE
}

repo_path=
task_file=
base_ref=
model_id=
provider_name=
stack_csv=
output_root=

while (($#)); do
  case "$1" in
    --repo) repo_path=${2:?missing value for --repo}; shift 2 ;;
    --task-file) task_file=${2:?missing value for --task-file}; shift 2 ;;
    --base-ref) base_ref=${2:?missing value for --base-ref}; shift 2 ;;
    --model-id) model_id=${2:?missing value for --model-id}; shift 2 ;;
    --provider) provider_name=${2:?missing value for --provider}; shift 2 ;;
    --stacks) stack_csv=${2:?missing value for --stacks}; shift 2 ;;
    --output-root) output_root=${2:?missing value for --output-root}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$repo_path" || -z "$task_file" || -z "$base_ref" || -z "$model_id" || -z "$provider_name" || -z "$stack_csv" ]]; then
  usage >&2
  exit 2
fi

repo_path=$(cd "$repo_path" && pwd)
task_file=$(cd "$(dirname "$task_file")" && pwd)/$(basename "$task_file")
[[ -d "$repo_path/.git" || -f "$repo_path/.git" ]] || { echo "Not a Git repository: $repo_path" >&2; exit 1; }
[[ -f "$task_file" ]] || { echo "Task file not found: $task_file" >&2; exit 1; }

if [[ -n "$(git -C "$repo_path" status --porcelain)" ]]; then
  echo "Repository has uncommitted changes; prepare a pristine snapshot first." >&2
  exit 1
fi

base_sha=$(git -C "$repo_path" rev-parse "$base_ref^{commit}")
repo_name=$(basename "$repo_path")
if [[ -z "$output_root" ]]; then
  output_root=${HIGHLANDER_RUN_ROOT:-$(dirname "$repo_path")/highlander-runs}
fi

run_dir="$output_root/${repo_name}-$(basename "$task_file" .md)-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$run_dir/worktrees" "$run_dir/stacks"

printf '%s\n' \
  "repository=$repo_path" \
  "task_file=$task_file" \
  "base_ref=$base_ref" \
  "base_sha=$base_sha" \
  "model_id=$model_id" \
  "provider=$provider_name" \
  "created_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "$run_dir/run-manifest.env"

IFS=',' read -r -a stack_names <<< "$stack_csv"
for stack_name in "${stack_names[@]}"; do
  [[ "$stack_name" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid stack name: $stack_name" >&2; exit 1; }
  worktree_path="$run_dir/worktrees/$stack_name"
  stack_dir="$run_dir/stacks/$stack_name"
  mkdir -p "$stack_dir"
  git -C "$repo_path" worktree add --detach "$worktree_path" "$base_sha" >/dev/null
  cp "$task_file" "$stack_dir/task-source.md"
  printf '%s\n' \
    "stack=$stack_name" \
    "worktree=$worktree_path" \
    "base_sha=$base_sha" \
    "model_id=$model_id" \
    "provider=$provider_name" \
    "auth_mode=record-before-run" \
    > "$stack_dir/stack-manifest.env"
  {
    printf '%s\n' \
      "Highlander match task: $(basename "$task_file")" \
      "Stack: $stack_name" \
      "Repository: $repo_name" \
      "Base SHA: $base_sha" \
      "Exact model requested: $model_id" \
      "Provider lane: $provider_name" \
      "Worktree: $worktree_path" \
      "" \
      "Use the task below unchanged. Do not merge, deploy, expose credentials, or modify benchmark scoring/evaluator material." \
      "At completion report the exact head SHA, tests actually run, unresolved risks, and cleanup state." \
      "" \
      "--- TASK ---"
    cat "$task_file"
  } > "$stack_dir/task-packet.md"
done

printf '%s\n' "Prepared Highlander match: $run_dir" "Base SHA: $base_sha" "Stacks: $stack_csv" "No agent was launched."

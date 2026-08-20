# Mobile Supervision Protocol

Highlander evaluates mobile supervision as a stack capability, not as a model capability. The coding runtime, model, task, repository snapshot, acceptance tests, and safety boundaries remain fixed. The treatment is the phone control path.

## Eligibility

A primary stack must provide a CLI workflow on macOS, Linux, and WSL, run inside or alongside Herdr, reuse legitimate provider subscriptions or authenticated native CLIs, and let the operator observe and respond to a session from a phone. Desktop apps may exist as optional conveniences but cannot be required.

The minimum baseline is Herdr's persistent session accessed from a phone SSH client. CCGram, OpenCode web, Claude Remote Control, MobileCLI, or another bridge is an additive treatment and must be recorded separately.

## Controlled exercise

1. Start two isolated sessions on different machines or disposable host profiles.
2. Use the same fixed model and task packet. Introduce one safe, visible decision boundary: an explicit clarification question or a permission prompt that cannot cause external damage.
3. Confirm the session is actually blocked from the local terminal and capture the session identity.
4. Observe the notification on the phone and respond with the minimum approved answer.
5. Reattach from a second computer and verify the same session identity, transcript, worktree, and current head SHA.
6. Disconnect the phone network, reconnect, and verify that no stale or duplicate input was delivered.
7. Finish the task, run validation, and inspect cleanup of sessions, worktrees, processes, ports, and bot/control-plane state.

## Recorded evidence

- platform and machine topology;
- phone channel and bridge version;
- session/agent identity before and after reattach;
- notification timestamp, response timestamp, and latency;
- screenshot or transcript of the blocked state and the response;
- whether the bridge sent raw keystrokes, structured input, or a provider-native response;
- missed, duplicated, misrouted, or stale input;
- provider/model/auth route and rate-limit errors;
- operator interaction classification;
- cleanup and security checks.

## Failure conditions

Disqualify the mobile treatment if it sends input to the wrong session, cannot distinguish blocked from idle, bypasses the approval boundary, loses required evidence, leaves material resources behind, or silently changes the model/provider route. A mobile bridge cannot receive coding-quality credit when the underlying runtime and model are unchanged.

## Recommended ablations

- `OMP + Herdr` with phone SSH baseline;
- `OMP + Herdr + CCGram` Telegram bridge;
- `Pi + Firstmate + Herdr` with phone SSH, then CCGram only after the base is stable;
- `OpenCode + Herdr` with phone SSH, then a separate OpenCode web/server test;
- watchlist-only tests for MobileCLI, ADHDev, and Fusion until their Herdr/WSL paths are proven.

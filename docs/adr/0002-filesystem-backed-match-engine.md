# Use a filesystem-backed Match Engine with Harness and Session ports

**Status:** Accepted

## Context

Highlander must run the same Task against several Contenders in isolated Arenas, expose the work in one terminal window, retain reproducible evidence, survive controller or terminal failures, and prevent the session multiplexer from becoming the source of truth. The initial implementation must remain portable across macOS, Linux, and WSL and must be testable without credentials or paid model calls.

Four designs were compared: a two-operation deep module, a phase-oriented ports-and-adapters engine, a fully resumable event-state machine, and a smallest-vertical-slice worker design. They agreed that harness protocols and pane placement are separate concerns. They differed mainly in how much lifecycle should be public and how much recovery infrastructure belongs in the pilot.

## Decision

Build one filesystem-backed `MatchRunner` with two stable operations: plan a Match and execute a frozen plan. The CLI presents `doctor`, `run`, `status`, and `stop`; dry-run is the default for `run`, and execution requires `--execute`.

Each Trial is hosted by an internal Highlander worker. A Session Adapter places that worker in Herdr, tmux, or a headless process. The worker communicates with its Harness through a native RPC, JSON, HTTP, stream, or ACP interface. Session Adapters never submit Task prompts, parse harness semantics, verify model controls, or decide qualification.

The MatchRunner owns:

- resolution of one base SHA and exact Task bytes;
- deterministic Match and Trial plans;
- isolated worktree preparation;
- an all-Trials-ready filesystem start gate;
- append-only lifecycle journals;
- control and evidence completeness checks;
- process/session cleanup and retained cleanup evidence.

Harness Adapters own:

- version and capability probing;
- native command/config construction;
- exact Task submission;
- structured lifecycle and native evidence capture;
- configured, runtime, and provider/wire control verification;
- native cancellation and ATIF projection.

Session Adapters own only worker placement, visible layout, process identity, terminal presentation capture, interruption, and pane/session cleanup. Herdr is the preferred operator experience; tmux is the portable fallback; headless and fake adapters support CI and scientific efficacy runs. Highlander never nests tmux inside Herdr.

The run directory is the recovery protocol. Workers announce readiness, wait on one atomic start-gate file, append events, and write terminal outcomes atomically. Prompt submission is not retried unless non-acceptance can be proven. Native traces are authoritative; ATIF is a derived interoperability view.

The pilot uses an explicit adapter registry, Python's standard library, fake Harness Adapters, headless execution, and a tmux Session Adapter. It does not add a daemon, database, scheduler, dynamic plugin system, Harbor runtime dependency, credential broker, or generic keystroke driver.

## Consequences

The architecture provides a safe common path, visible concurrent sessions, inspectable synchronization, deterministic fake tests, resumable evidence, and clean seams for OMP RPC and OpenCode JSON. It costs more per strict Harness Adapter than a universal command wrapper, but keeps model verification and evidence semantics local.

The first vertical slice can prove simultaneous prompt delivery and evidence capture without spending subscription quota. Real OMP-versus-OpenCode calibration remains blocked until both native adapters pass contract tests and strict model-control preflight.

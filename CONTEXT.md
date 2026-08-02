# Highlander

Highlander compares coding harnesses under controlled conditions. Its language separates the model, harness, session system, execution attempt, and retained evidence so a result can be attributed correctly.

## Language

**Gauntlet**:
The versioned collection of tasks, rules, controls, evaluators, and scoring used to compare harnesses.
_Avoid_: Benchmark suite, model benchmark

**Match**:
A comparison in which multiple Contenders attempt the same Task against the same Arena under one Control Profile.
_Avoid_: Run, leaderboard

**Trial**:
One Contender attempt within a Match. A Trial either produces a Qualified Result or is marked Invalid with explicit reasons.
_Avoid_: Agent run, model run

**Contender**:
A pinned harness and configuration being evaluated, including its Harness Adapter and declared capabilities.
_Avoid_: Agent, model, stack

**Harness**:
The coding runtime that mediates between the controlled model and the repository, tools, memory, permissions, subagents, and prompts.
_Avoid_: Model, agent

**Control Profile**:
The fixed model route, model identifier, reasoning level, model parameters, fallback policy, context and turn limits, and comparable execution constraints shared by every Contender in a primary Match.
_Avoid_: Model lane, provider setup

**Arena**:
The exact target repository snapshot and disposable environment used by every Trial in a Match.
_Avoid_: Workspace, project

**Task**:
The versioned prompt, acceptance criteria, boundaries, and evaluator contract presented unchanged to every Contender.
_Avoid_: Issue when no tracker issue is involved, prompt alone

**Harness Adapter**:
An adapter that translates Highlander launch, prompt, observation, interruption, and evidence requests into one Harness command surface.
_Avoid_: Wrapper, integration script

**Session Adapter**:
An adapter that places Trials into observable terminal sessions or panes and manages their lifecycle without defining Harness behavior.
_Avoid_: Multiplexer wrapper, pane script

**Capability Manifest**:
The pre-Trial declaration of the tools, memory, permissions, subagents, extensions, and other facilities a Harness exposes to the model.
_Avoid_: Feature list, config dump

**Evidence Bundle**:
The immutable artifacts required to reproduce and audit a Trial, including manifests, prompt, transcript, tool ledger, diff, validation, timing, operator interactions, and cleanup state.
_Avoid_: Logs, result files

**Qualified Result**:
A Trial outcome that passes all hard gates and has enough retained evidence to compare with other Trials in the Match.
_Avoid_: Success, winner

**Invalid Trial**:
A Trial that cannot support a harness comparison because a control changed, evidence is missing, execution was contaminated, or a hard gate failed.
_Avoid_: Loss, bad result

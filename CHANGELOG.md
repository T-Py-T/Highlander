# Changelog

This file records release and documentation changes only when they have inspectable evidence. It is intentionally thin until entries are added; the absence of an entry is not evidence of completion, release, readiness, or production status.

## Tip-cite and status

When recording a merged change, use:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

Use the first eight hexadecimal characters of the merge commit on `main` and the actual pull-request number. Resolve the tip against `main` only after the merge and pull request exist. Never use a branch tip, invent a tip or PR number, or reuse an older cite. A tip-cite records provenance only and never establishes `READY`. Untested, blocked, incomplete, or unresolved work must not be marked `READY`; do not invent a `READY` status, and a confident summary is not evidence by itself.

## Honesty footer

This changelog reports inspectable, version-bound changes; it does not claim production readiness, a universal winner, or completion when work is open, blocked, invalid, or incomplete. A missing changelog entry is not proof that a release or change is ready.

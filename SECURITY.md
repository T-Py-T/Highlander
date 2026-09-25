# Security policy

## Supported code

The current `main` branch is the only supported version. Highlander is a local benchmark tool and does not operate a hosted service.

## Report a vulnerability

Email the repository owner at [tnt850910@aol.com](mailto:tnt850910@aol.com). Include the affected commit, the vulnerable path, the impact, and the smallest reproduction that does not expose sensitive data.

Do not open a public issue for an unpatched vulnerability. You can expect an acknowledgment within seven days. A fix schedule depends on the severity and the affected component.

## Keep reports and evidence safe

- Do not send or commit API keys, tokens, provider credentials, authentication seeds, private prompts, proprietary task inputs, or personal data.
- Do not attach raw worktrees, provider caches, or unredacted transcripts.
- Use synthetic repositories and credentials when reproducing execution defects.
- Treat captured third-party output under its original license and terms.
- Run the local validation gate before sharing a proposed fix. Local checks do not certify a harness, provider, or generated change as secure.

## Tip-cite and status

When recording a merged security change, use this format:

```text
T-Py-T/Highlander <8-char-main-tip> PR#<number> — <short description>
```

Use the first eight hexadecimal characters of the merge commit on `main`, followed by the actual pull-request number. The Steward resolves the eight-character tip against `main`; cite it only after the merge and PR exist. Never use a branch tip, invent a tip or PR number, or reuse an older cite. A tip-cite records provenance only and is never `READY` by itself. Untested, blocked, or incomplete work must not be marked `READY`; do not invent a `READY` status, and a confident summary is not evidence by itself.

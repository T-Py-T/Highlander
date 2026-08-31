# Local release-gate record — 2026-08-31

This directory retains the local release checks for the two public Highlander hard-task seasons. GitHub Actions was not used while the account had no remaining hosted minutes.

## Evidence under test

| Season | Public artifact manifest SHA-256 | Artifacts |
|---|---|---:|
| `hb-devhard-hardcore-v1-gpt-5.6-luna-medium-r4` | `3c7e389a1df3339881083bab87de1a2374b7b0cfa8e32cf782575abea512c131` | 4,821 |
| `hb-devhard-hardcore-v1-gpt-5.4-medium-r1` | `a77fb20926e1134fa3d54167bb8630c1516c2a6c2d4599e3ab6c8787f7b3c1eb` | 6,090 |

## Gate history

1. `pre-commit-attempt-1.log` passed all hooks before the Linux portability correction.
2. `act-offline-attempt-1.log` failed one unit test because the test touched host-created extended attributes inside the Linux runner. The production behavior was unchanged; the test now mocks that platform boundary.
3. `pre-commit.log` passed 55 tests with two documented skips, compilation, doctor, fixture tests, shell syntax, and all four retained evidence verifiers.
4. `act-offline-attempt-2.log` passed the same tests but correctly exposed a clone-reproducibility defect: nested NanoBot `.gitignore` rules had kept 790 manifest-listed artifacts out of Git even though they existed in the local export. Exactly those manifest members were force-added: 408 for GPT-5.6 and 382 for GPT-5.4. Trial-level `artifact-manifest.json` files are retained separately by design.
5. `act-offline.log` is the successful post-fix run. In an offline, network-isolated Podman runner it passed 55 tests with two documented skips, MatchRunner validation, two fixture tests, shell syntax, and all four evidence verifiers. The GPT-5.6 and GPT-5.4 bundles verified at 4,821 and 6,090 artifacts respectively.
6. `clean-checkout.log` records a local `--no-local` clone of release commit `020e456`. From that fresh clone, every pre-commit hook passed again: 55 tests with two documented skips, compilation, MatchRunner validation, fixture tests, shell syntax, and all four evidence manifests.

Failed attempts are retained because they explain the fixes and make the release-gate history auditable. An invalid local gate never changes a benchmark score.

## Offline workflow result

`PASS` — the local GitHub Actions workflow completed with exit code 0, and release commit `020e456` reproduced from a fresh clone with every pre-commit hook passing. The post-verification documentation commit contains only this retained log and this status update.

# fake-t002-protocol-r1 evidence bundle

This is a **zero-cost protocol qualification**, not a coding-harness performance result. Deterministic fake Harness Adapters received the exact T002 task bytes, crossed the same start gate, emitted control proof, and were reconciled by the parent MatchRunner. No model was called.

| Proof | Value |
|---|---|
| Runner commit | `383b7a744e30295c24a7d2aca533f9fe6e272dc9` |
| Arena commit | `383b7a744e30295c24a7d2aca533f9fe6e272dc9` |
| Task SHA-256 | `30197b3a7a673b847ed586c6be7592e5375900cb380134732e31893cc1c650d9` |
| Plan SHA-256 | `b3a9f60ced131653ee59cdb780eb11aecbb94cd4ac99e119bb30c2b51e17ce6b` |
| Qualified trials | 2 / 2 |
| Start skew | 2.804 ms |

The fake success/failure outcomes exercise evidence semantics; they do not mean that T002 was solved. See `report/comparison.md` for the explicit claim boundary and `runner-provenance.json` for commit linkage.

From a Highlander checkout containing this bundle, verify every retained artifact with:

```text
python3 tools/evidence-bundle.py verify results/fake-t002-protocol-r1
```

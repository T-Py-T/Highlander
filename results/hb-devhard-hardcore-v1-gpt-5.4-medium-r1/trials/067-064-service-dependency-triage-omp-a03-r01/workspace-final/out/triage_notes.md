# Checkout incident triage notes

## Dependency path from user impact to root cause

[FACT] `in/logs/checkout-web.log` shows user-facing checkout submission failures: `submit_order failed status=401 upstream=payment-api` and `payment-api returned auth_failed invalid issuer`.

[FACT] `in/topology.json` shows the dependency chain `checkout-web -> payment-api -> auth-gateway`.

[FACT] `in/logs/payment-api.log` shows `create_payment` was rejected because upstream `auth-gateway` returned `issuer_not_allowed` for `issuer=partner-v2`.

[FACT] `in/logs/auth-gateway.log` shows change `AUTH-2026-0318` deployed at `2026-03-22T14:05:12Z` with `jwks_namespace=partner-v2` and `issuer=partner-v2`, then validation failed because `token_issuer=partner-v2` while `allowed_issuers=partner-v1`.

[INFERENCE] The production checkout incident was caused by an auth-gateway configuration regression introduced by `AUTH-2026-0318`: issuer rotation moved traffic to `partner-v2`, but `allowed_issuers` still effectively enforced `partner-v1`, causing token validation failures that propagated back through payment-api to checkout-web.

## Supporting observations

- [FACT] `in/metrics/service_metrics.csv` at `2026-03-22T14:10:00Z` shows elevated 401 rates on `auth-gateway` (28.4), `payment-api` (21.2), and `checkout-web` (18.7). The auth-gateway note explicitly says `jwks cache miss and issuer mismatch`.
- [FACT] `in/logs/auth-gateway.log` includes `rollback candidate: restore allowed_issuers partner-v2 or revert AUTH-2026-0318`.
- [FACT] `in/topology.json` lists `AUTH-2026-0318` as the only recent change on the impacted dependency path close to incident start.

## Excluded red herrings

- [FACT] `in/metrics/service_metrics.csv` shows `orders-db` CPU at 86%, but `p95_ms=35` and `http_5xx_rate=0.0`.
- [FACT] `in/logs/orders-db.log` says `no failed checkout transaction reached orders-db for request_id=req-8812`.
- [INFERENCE] `orders-db` was noisy but not causal because the failure happened upstream before order persistence.

- [FACT] `in/metrics/service_metrics.csv` shows `cdn-edge` 5xx errors with note `static asset 5xx isolated to images`.
- [FACT] `in/logs/checkout-web.log` says `static assets served normally after retry; user checkout flow still blocked`.
- [INFERENCE] CDN issues were concurrent noise, not the primary cause of checkout submission failures.

## Immediate mitigation

1. [ACTION] Revert `AUTH-2026-0318` on `auth-gateway`, or restore `allowed_issuers` so `partner-v2` is accepted.
2. [ACTION] Refresh the `auth-gateway` JWKS cache namespace after config correction so fallback behavior to `partner-v1` is cleared.
3. [ACTION] Monitor 401 rates on `auth-gateway`, `payment-api`, and `checkout-web` during rollback or config repair.

## Verification steps

1. [VERIFY] Confirm new `auth-gateway` logs show successful validation for `token_issuer=partner-v2` with no `issuer_not_allowed` errors.
2. [VERIFY] Confirm `payment-api` stops rejecting `create_payment` with `auth_result=invalid_issuer`.
3. [VERIFY] Confirm `checkout-web` no longer logs `submit_order failed status=401 upstream=payment-api` and its 401 rate returns near the `0.1` baseline from `in/metrics/service_metrics.csv`.
4. [VERIFY] Confirm no new evidence appears tying `orders-db` or `cdn-edge` to the checkout path after auth recovery.

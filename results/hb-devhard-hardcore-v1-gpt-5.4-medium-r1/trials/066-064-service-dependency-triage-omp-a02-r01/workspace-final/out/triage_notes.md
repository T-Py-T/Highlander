# Checkout incident triage

## Dependency path

Directly observed:
- User impact surfaced at `checkout-web`: `submit_order failed status=401 upstream=payment-api` and `payment-api returned auth_failed invalid issuer`.
- Topology maps the relevant path as `checkout-web -> payment-api -> auth-gateway` in `<SOURCE_EVIDENCE_ROOT>/trials/066-064-service-dependency-triage-omp-a02-r01/hb-work/omp/gpt-5.4/oc-bench-v2-064-service-dependency-triage-gpt-5.4-20260831-122403-2ab164e5/workspace/in/topology.json`.
- `payment-api` rejected `create_payment` with `auth_result=invalid_issuer` in `<SOURCE_EVIDENCE_ROOT>/trials/066-064-service-dependency-triage-omp-a02-r01/hb-work/omp/gpt-5.4/oc-bench-v2-064-service-dependency-triage-gpt-5.4-20260831-122403-2ab164e5/workspace/in/logs/payment-api.log`.
- `auth-gateway` deployed `AUTH-2026-0318`, then logged `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1` in `<SOURCE_EVIDENCE_ROOT>/trials/066-064-service-dependency-triage-omp-a02-r01/hb-work/omp/gpt-5.4/oc-bench-v2-064-service-dependency-triage-gpt-5.4-20260831-122403-2ab164e5/workspace/in/logs/auth-gateway.log`.

Inference:
- The production checkout failure chain is: partner token presented to `checkout-web` -> `payment-api` asks `auth-gateway` to validate it -> `auth-gateway` rejects `partner-v2` because its allowed issuer set remained `partner-v1` after `AUTH-2026-0318` -> `payment-api` returns 401 -> checkout submission fails.
- Highest-probability root cause is a bad auth-gateway rollout or incomplete config cutover in `AUTH-2026-0318`, likely combining issuer rotation with mismatched allowed issuer state and JWKS namespace transition.

## Evidence summary

Directly observed:
- `<SOURCE_EVIDENCE_ROOT>/trials/066-064-service-dependency-triage-omp-a02-r01/hb-work/omp/gpt-5.4/oc-bench-v2-064-service-dependency-triage-gpt-5.4-20260831-122403-2ab164e5/workspace/in/metrics/service_metrics.csv` shows 14:10Z 401 spikes aligned along the dependency chain: `auth-gateway` 28.4%, `payment-api` 21.2%, `checkout-web` 18.7%.
- `<SOURCE_EVIDENCE_ROOT>/trials/066-064-service-dependency-triage-omp-a02-r01/hb-work/omp/gpt-5.4/oc-bench-v2-064-service-dependency-triage-gpt-5.4-20260831-122403-2ab164e5/workspace/in/logs/orders-db.log` shows `p95_query_ms=35` and `errors=0`, with no failed checkout transaction reaching the DB for `req-8812`.
- `<SOURCE_EVIDENCE_ROOT>/trials/066-064-service-dependency-triage-omp-a02-r01/hb-work/omp/gpt-5.4/oc-bench-v2-064-service-dependency-triage-gpt-5.4-20260831-122403-2ab164e5/workspace/in/logs/checkout-web.log` says static assets recovered while checkout remained blocked.

Inference:
- `orders-db` CPU and `cdn-edge` image 5xxs are concurrent noise, not the cause of the checkout auth failures.

## Immediate mitigation

Directly observed:
- `auth-gateway.log` explicitly records: `rollback candidate: restore allowed_issuers partner-v2 or revert AUTH-2026-0318`.

Recommended action:
1. Restore `partner-v2` to `auth-gateway` allowed issuers or revert `AUTH-2026-0318`.
2. Flush or rebuild the `partner-v2` JWKS cache namespace after the config rollback/fix.
3. Keep focus on `auth-gateway`, `payment-api`, and `checkout-web`; do not lead with DB or CDN mitigation for this incident.

## Verification steps

After mitigation, verify:
1. Replay a checkout using a `partner-v2` token and confirm `auth-gateway` no longer emits `issuer_not_allowed`.
2. Confirm `payment-api` no longer logs `create_payment rejected ... auth_result=invalid_issuer`.
3. Confirm `checkout-web` no longer returns `submit_order failed status=401 upstream=payment-api` for the same path.
4. Confirm service metrics move back toward baseline 401 rates in the same chain: `auth-gateway`, `payment-api`, `checkout-web`.

## Excluded red herrings

Directly observed:
- `orders-db` had `cpu=86` during vacuum, but query latency remained normal and no failing checkout reached it.
- `cdn-edge` had `4.8` 5xx rate isolated to static images, but checkout-web reported user flow still blocked after assets recovered.

Inference:
- These signals may have paged operators, but they do not explain the invalid-issuer rejection pattern driving the checkout outage.

# Checkout dependency triage

## Conclusion

**Root cause:** `auth-gateway`, change `AUTH-2026-0318`, with high confidence.

The dependency path is:

`user checkout submit -> checkout-web -> payment-api -> auth-gateway`

`orders-api -> orders-db` is a separate branch and is not reached before the failing payment authorization gate.

## Evidence and dependency path

- **Directly observed** in `in/topology.json`: `checkout-web` depends on `payment-api`, and `payment-api` depends on `auth-gateway`. The same fixture records `AUTH-2026-0318` on `auth-gateway` at `2026-03-22T14:05:00Z`, changing the issuer and JWKS cache namespace.
- **Directly observed** in `in/logs/auth-gateway.log`: the deployment uses `partner-v2`, but validation at `14:08:34Z` rejects token issuer `partner-v2` because `allowed_issuers=partner-v1`. The log itself names restoring `partner-v2` or reverting `AUTH-2026-0318` as rollback candidates.
- **Directly observed** in `in/logs/payment-api.log`: payment authorization reports `issuer_not_allowed` from `auth-gateway`, then `create_payment` rejects request `req-8812` with `invalid_issuer`. The log says the order database was not used before the auth gate.
- **Directly observed** in `in/logs/checkout-web.log`: `submit_order` returns 401 from `payment-api`; a later asset retry succeeds, but the checkout flow remains blocked.
- **Directly observed** in `in/metrics/service_metrics.csv`: at `14:10Z`, HTTP 401 rates are 18.7% for checkout-web, 21.2% for payment-api, and 28.4% for auth-gateway. Payment and auth notes explicitly identify invalid issuer / issuer mismatch.

**Inference:** the issuer/allow-list mismatch introduced by `AUTH-2026-0318` is the primary causal fault. It propagates upstream from auth-gateway to payment-api and then to checkout-web, explaining the user-visible checkout rejection and latency increase. The timing, matching error text, topology, and direct request chain support this inference; the fixture does not provide runtime traces beyond the listed request.

## Misleading signals excluded

- `orders-db` CPU is 86%, but **directly observed** in `in/metrics/service_metrics.csv` and `in/logs/orders-db.log`: query p95 is 35 ms with zero errors, and no failed checkout transaction reached the database. This is not the primary cause.
- `cdn-edge` has a 4.8% 5xx rate, but **directly observed** in `in/metrics/service_metrics.csv`: the errors are isolated to images. `in/logs/checkout-web.log` says assets served normally after retry while checkout remained blocked. CDN is not on the failing authorization chain.
- Checkout/payment latency and 5xx changes are **inferred downstream symptoms**, not the root cause: the directly observed 401/invalid-issuer failures occur at the auth dependency and are propagated through the topology.

## Immediate mitigation

1. Halt or roll back `AUTH-2026-0318`, **or** restore `partner-v2` to `auth-gateway`'s allowed issuer set and align the JWKS cache namespace.
2. Refresh/invalidate the auth-gateway JWKS cache after the configuration change.
3. Do not make orders-db or CDN changes as the checkout mitigation; keep those as separate investigations if their independent alerts persist.

## Verification

1. **Direct check:** confirm auth-gateway accepts a controlled valid `partner-v2` token and no longer logs `issuer_not_allowed`.
2. **Direct check:** run a controlled payment authorization / `create_payment` request and confirm success through payment-api.
3. **Direct check:** replay one controlled checkout `submit_order` and confirm checkout-web receives a successful response rather than 401.
4. **Metric check:** confirm auth-gateway, payment-api, and checkout-web HTTP 401 rates fall toward the `14:00Z` baseline; confirm checkout p95 falls from 2400 ms toward baseline. These expected post-mitigation outcomes are **inferences**, not observations in the supplied fixtures.

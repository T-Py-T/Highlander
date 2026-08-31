**Incident Summary**

Directly observed fact: the user impact is failed checkout submissions at `checkout-web`, which logged `submit_order failed status=401 upstream=payment-api` and `invalid issuer` in `/workspace/in/logs/checkout-web.log`.

Directly observed fact: `payment-api` rejected the same failing request because token validation from `auth-gateway` returned `issuer_not_allowed` / `invalid_issuer` in `/workspace/in/logs/payment-api.log`.

Directly observed fact: `auth-gateway` deployed `AUTH-2026-0318` shortly before the incident, switched to `issuer=partner-v2`, then logged `validation failed reason=issuer_not_allowed token_issuer=partner-v2 allowed_issuers=partner-v1` in `/workspace/in/logs/auth-gateway.log`.

Inference: the production checkout incident was caused by an auth-gateway configuration regression introduced by `AUTH-2026-0318`, where the issuer/JWKS namespace moved to `partner-v2` without updating the effective allowed issuer set.

**Dependency Path**

Directly observed fact: `/workspace/in/topology.json` shows `checkout-web -> payment-api -> auth-gateway` on the failing path.

Directly observed fact: `/workspace/in/metrics/service_metrics.csv` shows synchronized 401 spikes at 14:10Z across `auth-gateway` (28.4%), `payment-api` (21.2%), and `checkout-web` (18.7%), with notes explicitly mentioning `issuer mismatch` and `invalid issuer`.

Inference: the dependency path from user impact to root cause is:

`checkout-web` user checkout failure -> `payment-api` rejects payment creation -> `auth-gateway` denies partner token due to issuer mismatch introduced by `AUTH-2026-0318`.

**Why Other Signals Are Not Primary**

Directly observed fact: `/workspace/in/logs/orders-db.log` reports `cpu_high cpu=86 pct maintenance=vacuum`, but also `p95_query_ms=35`, `errors=0`, and `no failed checkout transaction reached orders-db for request_id=req-8812`.

Inference: `orders-db` load is a red herring and not on the causal path for the observed checkout failures.

Directly observed fact: `/workspace/in/metrics/service_metrics.csv` shows `cdn-edge` 5xx isolated to static assets, and `/workspace/in/logs/checkout-web.log` says static assets served normally after retry while checkout remained blocked.

Inference: the CDN issue is concurrent noise, not the primary cause of payment authorization failure.

**Immediate Mitigation**

1. Restore `auth-gateway` allowed issuers to include `partner-v2`, or roll back `AUTH-2026-0318`.
2. Rebuild or flush the `partner-v2` JWKS cache namespace after the issuer configuration is corrected.
3. If rollback is chosen, confirm the gateway again validates tokens issued as `partner-v1` or the intended partner issuer set.

**Verification Steps**

1. Check `auth-gateway` logs for disappearance of `issuer_not_allowed` and JWKS fallback warnings in `/workspace/in/logs/auth-gateway.log` equivalent live logging.
2. Check `payment-api` for the end of `auth_result=invalid_issuer` rejections like the ones seen in `/workspace/in/logs/payment-api.log`.
3. Check `checkout-web` that `submit_order` 401s clear and p95 latency returns toward the 14:00Z baseline from `/workspace/in/metrics/service_metrics.csv`.
4. Confirm no new dependency failures appear on adjacent services after mitigation, especially along the `checkout-web -> payment-api -> auth-gateway` path from `/workspace/in/topology.json`.

**Bottom Line**

Inference: with the available offline evidence, `auth-gateway` is the root-cause service and `AUTH-2026-0318` is the most likely triggering change.

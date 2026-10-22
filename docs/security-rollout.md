# Security rollout

Prepared on 22 October 2026 for the Synapse findings in the supplied security report. Commit, push, and deployment were authorised on that date. Verify the current Git and Render state before resuming rollout; the steps below also describe separate credential and database operations.

## Changes

| Finding | Implemented behaviour |
| --- | --- |
| S1 | Reset requests return a generic acknowledgement. Account lookup and email delivery happen after the response. Resend emails a code to the account address; the API never returns it. |
| S2 | `certifi` is locked to 2026.10.19. The project requires uv >=0.13.4. The Render build script verifies the patched pip 26.2.2 wheel before bootstrapping uv 0.13.4, then installs the frozen dependencies and patched pip. |
| S3 | Demo tokens expire after one day. Regular tokens expire after seven days. Backend and frontend reject legacy tokens without expiry. |
| S4 | Per-IP limits cover every auth route. Registration and reset both require eight-character passwords. Email verification remains a separate product change. |
| S5 | Unexpected HTTP and streaming errors return generic messages; details stay in server logs. |
| S6 | Reset codes use 256 bits of randomness. Only versioned SHA-256 hashes are stored in the existing `token` column. Issuance replaces the user's old tokens. Confirmation updates the password and consumes all reset tokens for the user in one transaction. Legacy plaintext tokens are rejected. |

The SurrealDB Python SDK's `query()` returns only the first statement result. Auth transactions inspect every `query_raw()` result, including failures at commit, before reporting success.

## Configure before deployment

On the **Synapse backend** Render service, set `RESEND_API_KEY` and `RESET_EMAIL_FROM` using a sender on a verified domain. Without them, the reset endpoint still returns the generic acknowledgement, logs a configuration error, and issues no code. Provider failures also keep the response generic and invalidate the newly issued code.

Both Python services use `bash scripts/build-backend.sh`. The backend starts with `.venv/bin/uvicorn`; the Telegram worker starts with `.venv/bin/python`. If the services have manually managed build/start commands, apply the commands from `render.yaml` in the dashboard too. Both services must rebuild so their runtime certificate bundles are updated.

The bootstrap wheel hash and minimum versions follow the [Python security announcement](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576). This changes this project's environment and build commands, not globally installed tools or the operating system trust store.

## Rate limits

| Endpoint | Requests per IP |
| --- | --- |
| Register | 5 per hour |
| Login | 10 per minute |
| Demo login | 30 per minute |
| Request reset | 3 per hour |
| Confirm reset | 10 per minute |

The default storage is process-local memory. It resets on restart and is appropriate only for a single API process/instance. Before scaling, install the `redis` extra and set `RATELIMIT_STORAGE_URI` to shared Redis storage. Use a persistent store if limits must survive restarts.

The limiter reads the ASGI client address and does not parse untrusted forwarding headers. Configure Uvicorn's `FORWARDED_ALLOW_IPS` for the deployment's actual trusted proxy addresses. Verify that two independent clients receive different limiter identities on Render before rollout. Do not broadly trust arbitrary forwarding headers. Recheck legitimate traffic against the chosen thresholds.

## Production rollout, requires approval

Targets: the Synapse backend and Telegram worker's shared `JWT_SECRET`, and the shared Synapse SurrealDB database's `reset_token` table. These are the only proposed production credential/data changes; none have been executed.

1. Review the local diff and test results, then approve committing/pushing the change and deploying all services.
2. Confirm the intended deployed commit, email configuration, and patched Python dependencies on both services.
3. Rotate `JWT_SECRET` consistently on the backend and Telegram worker and restart both. This signs everyone out, including any sessions created before the fix. Existing seven-day tokens are otherwise valid until expiry; per-user session revocation is not implemented.
4. Preview outstanding reset rows with `SELECT id, user_id, expires_at FROM reset_token;`. After explicit approval for that database target, invalidate the outstanding rows with `DELETE reset_token;`. The new code already rejects legacy plaintext rows, but deletion removes the stored credentials.
5. Test recovery using an account you control. Known and unknown emails must receive the same HTTP status/body. Only the known account should receive an email. Confirm the code works once, a previous code fails after a new request, and reset passwords shorter than eight characters fail. Check rate limits and generic errors using controlled requests.
6. Verify the public frontend loads and automatically obtains a fresh expiring demo token. Do not treat a successful build as proof of production completion.

## Local verification

Use synthetic credentials and a disposable local database. Tests refuse non-loopback database URLs. No real emails or model calls are made.

```sh
uv sync --frozen --group security --group audit
uv run pytest
# To include transaction and concurrency integration checks, start SurrealDB 3.0.1:
surreal start --bind 127.0.0.1:18081 --user test --pass test memory
SYNAPSE_TEST_SURREAL_URL=ws://127.0.0.1:18081/rpc uv run pytest
uv run --group security --group audit pip-audit
cd frontend
npm ci --ignore-scripts
npm run build
npm audit
```

## Outstanding dependency findings

The compatible updates clear the frontend audit and most Python findings. The final Python audit still reports **15 advisory entries across five packages** (nine distinct advisory IDs). No advisories were suppressed:

| Package | Locked version | Advisory IDs |
| --- | --- | --- |
| langchain-anthropic | 1.2.0 | PYSEC-2026-2556 |
| langchain-core | 1.1.3 | PYSEC-2026-373, PYSEC-2026-2193, PYSEC-2026-2562, PYSEC-2026-2563, PYSEC-2026-2564 |
| langchain-openai | 1.1.3 | PYSEC-2026-76 |
| langgraph-checkpoint | 4.0.1 | PYSEC-2026-2573 |
| langgraph-sdk | 0.3.15 | PYSEC-2026-4240 |

`langchain-surrealdb` 0.2.0 declares `langchain-core~=1.1.0`, blocking the patched LangChain core and provider packages. The patched checkpoint imports `Reviver(allowed_objects=...)`, which is incompatible with that old core. LangGraph's stable release constrains its SDK to `<0.4.0`, blocking the SDK's patched version. Resolving these requires a coordinated integration/framework migration with vector-store, agent, and checkpoint validation. This task does not override those upstream constraints or claim a clean Python audit.

PyJWT is updated to 2.15.1 and is clear in the final audit. JWT decoding also constructs a fresh options mapping on each call.

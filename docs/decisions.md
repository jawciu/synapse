# Decisions

## 22 October 2026: Password recovery and dependency compatibility

Password recovery sends an emailed code through Resend and retains the existing manual code-entry form. It does not add token-bearing URLs or guess a frontend hostname. The existing reset-token column stores a versioned SHA-256 hash, which rejects legacy plaintext tokens without changing the production schema at startup. Issue/consume operations are transactions, and every SurrealDB statement result is checked before success is reported.

Demo JWTs last one day and all verified JWTs require expiry. Existing user sessions require a shared secret rotation for immediate global revocation; per-user revocation and signup email verification remain separate changes.

Auth limits use SlowAPI with process-local storage by default and support an optional Redis backend for shared limits. The deployment must validate its trusted proxy configuration.

Compatible security dependency updates are included. Upstream LangChain/SurrealDB and LangGraph constraints prevent five remaining packages from reaching patched versions. A standalone checkpoint upgrade breaks imports against the old core, so those constraints remain intact pending a coordinated migration. See `security-rollout.md` for the exact packages and advisories.

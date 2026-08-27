# Evaluation oracle

- The old global role check did not bind access to the requested account.
- The new order resolves the account, checks membership on that account, and only then loads the report.
- Admin cross-account access stays valid.
- Missing and denied accounts keep the same public response to avoid account discovery.
- The questions must test the trust boundary and its effect, not method or file recall.
- Post-answer examples can contrast an analyst for A requesting B with an admin requesting B. The first is denied; the second retains access when B exists.
- A flow that claims report loading happens before authorization is wrong. A membership claim needs the permissions file; the endpoint file supports lookup order and the shared public response.
- The diff does not establish audit logging, membership refresh, or timing equality. Do not invent those guarantees.

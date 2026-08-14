# Evaluation oracle

- The old global role check did not bind access to the requested account.
- The new order resolves the account, checks membership on that account, and only then loads the report.
- Admin cross-account access stays valid.
- Missing and denied accounts keep the same public response to avoid account discovery.
- The questions must test the trust boundary and its effect, not method or file recall.

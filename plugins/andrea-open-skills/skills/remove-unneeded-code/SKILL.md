---
name: remove-unneeded-code
description: Review a planned or current code change to remove code that is not required. Use when the user asks to simplify a change, remove unnecessary code, reduce complexity, or review a diff for needless additions.
---

# Remove Unneeded Code

Review the requested change one file at a time.

For each addition, ask:

- Is this needed for the request?
- Was this part of the requirements?
- Can the same result use less code without making it harder to read?
- What assumption added this code? Is that assumption needed?

## Preserve behavior

Simplify the implementation, not its behavior. Before editing:

1. List the behavior provided by the code under review.
2. Treat existing behavior tests as requirements.
3. Check affected callers, permissions, error paths, and user types.
4. Explain why the smaller implementation preserves each behavior.

Do not change or remove a behavior test because simpler code fails it. Change
such a test only when the user explicitly changes the required behavior or the
same behavior remains covered elsewhere.

If behavior equivalence cannot be proved, do not edit. Report the possible
simplification and ask whether the behavior may change.

Remove code only when evidence shows that no required or existing behavior
depends on it. Prefer an existing simple path to a new helper, option, fallback,
or abstraction.

Do not use code tricks to make a diff shorter. Keep clear conditions and names.
Do not change behavior or unrelated code.

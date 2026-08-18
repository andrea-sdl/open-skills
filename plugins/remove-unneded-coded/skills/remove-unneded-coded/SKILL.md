---
name: remove-unneded-coded
description: Review a planned or current code change to remove code that is not required. Use when the user asks to simplify a change, remove unnecessary code, reduce complexity, or review a diff for needless additions.
---

# Remove Unneded Coded

Review the requested change one file at a time.

For each addition, ask:

- Is this needed for the request?
- Was this part of the requirements?
- Can the same result use less code without making it harder to read?
- What assumption added this code? Is that assumption needed?

Remove code when the answer shows that it is not needed. Prefer an existing
simple path to a new helper, option, fallback, or abstraction.

Do not use code tricks to make a diff shorter. Keep clear conditions and names.
Do not change behavior or unrelated code.

If removing code would change a stated requirement or known behavior, explain
the assumption and ask before making that change.

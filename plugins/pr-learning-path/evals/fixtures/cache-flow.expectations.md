# Evaluation oracle

- Partial provider data must stay request-local and must never become a shared complete entry.
- Validation happens before one replacement of the shared cache entry.
- A failed refresh with a warm cache returns the last complete entry.
- A failed first load still returns unavailable because no safe fallback exists.
- The key and TTL remain unchanged for current consumers.
- The final synthesis must connect partial publication, atomic replacement, fallback flow, and what consumers observe.

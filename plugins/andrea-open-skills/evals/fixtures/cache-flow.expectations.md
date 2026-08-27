# Evaluation oracle

- Partial provider data must stay request-local and must never become a shared complete entry.
- Validation happens before one replacement of the shared cache entry.
- A failed refresh with a warm cache returns the last complete entry.
- A failed first load still returns unavailable because no safe fallback exists.
- The key and TTL remain unchanged for current consumers.
- The final synthesis must connect partial publication, atomic replacement, fallback flow, and what consumers observe.
- Post-answer examples should distinguish a provider failure with an existing complete entry from a provider failure with no entry. Partial request-local data is never the fallback.
- Loader claims need the loader file; fallback and unavailable-response claims need the service file. An explanation spanning both needs both source paths.
- The service catches ProviderError only. The diff does not show the exception type from validation, retry scheduling, concurrency locks, or compare-and-swap ordering. Do not claim all failures get fallback or that old refreshes cannot overwrite newer ones.

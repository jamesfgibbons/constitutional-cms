# Canonical JSON and receipt identity

Constitutional CMS digests logical contract data, not YAML bytes or whitespace. Implementations MUST apply this
procedure to a parsed JSON-compatible value:

1. encode objects with keys sorted lexicographically by Unicode code point;
2. preserve array order;
3. emit JSON primitives without insignificant whitespace;
4. encode strings as UTF-8 with non-ASCII characters preserved;
5. hash the resulting UTF-8 bytes with SHA-256 and emit lowercase hexadecimal.

The Python reference expression is:

```python
hashlib.sha256(
    json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
```

Catalog and evidence digests use the parsed catalog and evidence bundle. `result_digest` uses the complete normalized
receipt with the `result_digest` member omitted. The evaluation context includes `as_of`, `catalog_digest`,
`evidence_digest`, and `evaluator_version`. `as_of` defaults to the evidence bundle's `collected_at`; the runtime clock
never silently changes receipt identity. Implementations that accept numbers outside interoperable JSON number ranges
MUST reject them before canonicalization.

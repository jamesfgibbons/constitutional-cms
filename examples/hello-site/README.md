# Hello site (synthetic)

**Provenance mode: synthetic**

`evidence.yaml` is a domain-neutral teaching bundle. It is not a customer page, a production measurement, or a certification.

Use it to learn the CLI loop:

1. Produce a receipt.
2. Change one observation (for example `observations.http.status`).
3. See the verdict change.
4. Add `--fail-on FAIL` only when a catalog `FAIL` should block publication.

```bash
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json
```

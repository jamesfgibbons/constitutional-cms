# CLI reference

The product page is the [README](../README.md). This page is the extra flags.

Default `audit` writes a receipt and exits `0`. That is intentional: the command is a receipt generator. CI that should block a release must opt in with `--fail-on`.

## Custom catalog or evaluation timestamp

```bash
constitutional-cms audit \
  --catalog contracts/check_catalog_v1.yaml \
  --evidence examples/hello-site/evidence.yaml \
  --as-of 2026-08-15T12:00:00Z
```

## Public URL (observe-only)

One read-only GET. Static evidence only. Everything a static response cannot observe stays `UNMEASURED`.

```bash
constitutional-cms audit https://example.com
constitutional-cms audit https://example.com --json
```

Prefer `--evidence` in CI.

## Validate

With no arguments, `validate` checks that the **bundled** catalog and schemas are internally coherent. That works from a wheel, outside this clone. If `./contracts` exists, it is validated too.

```bash
constitutional-cms validate
constitutional-cms validate path/to/contracts --check links
```

## No-install scripts

```bash
python scripts/validate_contracts.py
python scripts/validate_web_conformance.py
python scripts/conformance_evaluator.py \
  --evidence tests/fixtures/conformance/pass_all.yaml
python scripts/page_health_validator.py
```

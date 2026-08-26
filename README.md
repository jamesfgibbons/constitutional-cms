# Constitutional CMS

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue.svg)](pyproject.toml)
[![Release](https://img.shields.io/github/v/release/jamesfgibbons/constitutional-cms)](https://github.com/jamesfgibbons/constitutional-cms/releases/tag/v0.5.0)

Open-source **publishing governance for AI-built websites**.

**Govern what agents publish. Prove it with a receipt.**

Constitutional CMS governs the right to publish. VIBEnet governs the right to notice. Neither impersonates the other.

The public checker inspects what reached the web. The CLI runs the same evidence rules before publication.

[Run a public audit](https://constitutionalcms.com/check) · [CLI](#install-and-run-a-fixture) · [Protocol](docs/WEB_CONFORMANCE.md) · [Pilot](https://constitutionalcms.com/pilot)

CMS used to mean Content Management System — software for humans who write pages. Constitutional CMS manages the *contracts* that govern what AI agents are permitted to publish.

## Website vs CLI

| | After publication | Before publication |
|---|---|---|
| **Surface** | [constitutionalcms.com/check](https://constitutionalcms.com/check) | `constitutional-cms` CLI |
| **Input** | A public URL | Normalized `EvidenceBundleV1` |
| **Question** | What did the outside world receive? | Can our own system run the same rules before the next page ships? |

Do not trust the hosted checker as the last word. Download the evidence and re-run the same verdict locally.

## Install and run a fixture

Verified 2026-08-23 on a clean machine (no checkout `PYTHONPATH`, directory was not an existing clone). Homebrew Python is PEP 668-managed, so the command that **worked** is clone + venv. Bare `python3 -m pip install -e .` failed. PyPI / `uvx` still 404 — do not use them yet.

```bash
git clone --branch v0.5.0 --depth 1 https://github.com/jamesfgibbons/constitutional-cms.git
cd constitutional-cms
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python3 -m pip install -e .
constitutional-cms validate
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json
```

![Fixture audit writing receipt.json with certified: false](docs/assets/quickstart.gif)

```text
$ constitutional-cms audit --evidence examples/hello-site/evidence.yaml --out receipt.json
$ python3 -c "import json; print('certified:', json.load(open('receipt.json'))['certified'])"
certified: false
```

The command is quiet and exits `0`: it writes a receipt, it does not print a score. `certified: false` is correct. This public path recreates a check; it does not certify a site.

Default `audit` writes a receipt and exits `0`. CI that should block a release must opt in:

```bash
constitutional-cms audit \
  --evidence examples/hello-site/evidence.yaml \
  --out receipt.json \
  --fail-on FAIL
```

More flags: [`docs/CLI.md`](docs/CLI.md).

After PyPI serves `constitutional-cms` 0.5.0 from tag `v0.5.0` (not before):

```bash
pip install constitutional-cms
# or uvx constitutional-cms …
```

## Sample receipt (abridged)

Provenance: synthetic fixture. Not a live customer page. `certified` is always `false` on this public recreate-a-check path.

```json
{
  "schema_version": "ConformanceReceiptV1",
  "framework_release": "v0.5.0",
  "catalog_version": "1.0.2",
  "certified": false,
  "checks": [
    {
      "check_id": "web.http.success",
      "verdict": "PASS",
      "reason_code": "rule_satisfied"
    },
    {
      "check_id": "web.accessibility.automated",
      "verdict": "UNMEASURED",
      "reason_code": "evidence_missing"
    }
  ]
}
```

A score collapses “wrong,” “not applicable,” and “not observed” into one number. Constitutional CMS keeps them separate.

## What it does — and does not do

It does:

- evaluate normalized evidence against a versioned 19-check catalog
- keep `PASS`, `FAIL`, `UNMEASURED`, and `NOT_APPLICABLE` as distinct verdicts
- emit a `ConformanceReceiptV1` with evidence pointers and a result digest
- refuse to invent a pass, a fail, or a composite score

It is not:

- another SEO crawler
- another content generator
- a replacement for WordPress, Webflow, or a headless CMS
- general-purpose agent permission management
- a proprietary website score
- an observability dashboard

Agent-security products govern what tools an agent can call. Constitutional CMS governs what the resulting public surface is allowed to claim.

## Release identity

| Coordinate | Value |
|---|---|
| Framework release | `v0.5.0` |
| Python package | `0.5.0` |
| Check catalog | `1.0.2` (19 checks) |
| Git tag | `v0.5.0` (`1cffaf5`) |

The hosted checker, this repository, the Python package, and the changelog must name the same commit. See [CHANGELOG.md](CHANGELOG.md) and [ROADMAP.md](ROADMAP.md).

## Adoption ladder

1. Run a fixture.
2. Produce a receipt.
3. Change one evidence value.
4. See the verdict change.
5. Add your own collector or adapter.
6. Enforce the receipt in CI (`--fail-on FAIL` when you mean it).

## Three contribution paths

| Path | What you file | Open work |
|---|---|---|
| **Incident** | What broke in a real publishing system | [production-incident](.github/ISSUE_TEMPLATE/production-incident.yml) |
| **Invariant** | The portable rule that failure generalizes to | [contribute-invariant](.github/ISSUE_TEMPLATE/contribute-invariant.yml) |
| **Adapter** | A translator into `EvidenceBundleV1` / `LinkTargetV1` | [#28](https://github.com/jamesfgibbons/constitutional-cms/issues/28) static HTML → evidence · [#30](https://github.com/jamesfgibbons/constitutional-cms/issues/30) sitemap → `LinkTargetV1` · [template](.github/ISSUE_TEMPLATE/contribute-adapter.yml) |

Also open: [#29](https://github.com/jamesfgibbons/constitutional-cms/issues/29) GitHub Actions audit workflow · [#32](https://github.com/jamesfgibbons/constitutional-cms/issues/32) interop receipt validation.

Issues are for concrete work. Implementation questions belong in [Discussions](https://github.com/jamesfgibbons/constitutional-cms/discussions).

**Skills make agents capable. Contracts make agents trustworthy.**

---

## Reference

The long constitution is not the landing page. Read it after you have a receipt.

- [Constitution](docs/CONSTITUTION.md) — five contracts, priority stack, agent rules
- [Protocol map](docs/PROTOCOL_MAP.md) — which scheme answers which question
- [Publishing heuristics](docs/PUBLISHING_HEURISTICS.md) — smells, not checks; children require a hub
- [Consuming layer](docs/CONSUMING_LAYER.md) — the universe law; unauthorized certainty, not a style guide
- [Entity lifecycle](docs/ENTITY_LIFECYCLE.md) — Gone is a verdict; 410 needs terminal authority
- [Web conformance](docs/WEB_CONFORMANCE.md) — profiles, verdicts, `UNMEASURED`
- [CLI flags](docs/CLI.md)
- [Novelty](docs/NOVELTY.md) · [Prior art](docs/PRIOR_ART.md) · [Source boundary](docs/SOURCE_BOUNDARY.md)

## License

Apache 2.0. The spec and pattern are open. Your domain-specific contracts are your competitive advantage.

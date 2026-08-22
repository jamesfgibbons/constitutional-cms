# Roadmap

Constitutional CMS is publishing governance for AI-built websites. This file is the public adoption sequence, not a scoreboard of activity.

## Now — v0.5.0

- Distribution identity: framework `v0.5.0`, package `0.5.0`, catalog `1.0.2` (19 checks), one git tag.
- PyPI / `uvx` after a clean-wheel proof from outside this repository.
- Hosted checker and CLI evaluate the same catalog.
- Hosted checker refuses to judge intercepted challenge pages (`BLOCKED_BY_TARGET`).
- Catalog verdicts stay distinct from public-wire diagnostic packs.

## Next

- Reusable GitHub Actions workflow that runs `constitutional-cms audit --fail-on FAIL`.
- Minimal static HTML evidence collector (good first issue).
- Sitemap → `LinkTargetV1` adapter example.
- Receipt verification command.
- First external implementation pinning this release.

## Later

- Additional collectors.
- Adapter gallery.
- Receipt registry.
- Hosted organizational workflows (Claim Gate), not a second scoring engine.

VIBEnet Signal Contract remains adjacent: it governs how a finding may enter human attention after the verdict exists. It is not a Constitutional CMS profile.

# How Agents Use These Contracts

## The Pattern

```
Agent reads contract → Agent writes code → Eval checks live site → Pass or fail
```

There is no orchestrator. There is no message bus. The contract declares what should be true. The agents make it true. The eval verifies it is true.

## Before Starting Work

Every agent, regardless of framework (Claude, GPT, Codex, local model, human), follows this sequence:

1. **Read the priority stack.** If Level 1 (data truth) is broken, do not work on Level 3 (content depth).
2. **Read the relevant contract.** If you're building an entity page template, read `page_types.yaml`. If you're writing a data pipeline, read `enrichment_stages.yaml`.
3. **Identify your boundary.** Are you a write agent or a read agent? Check `snapshot_boundary.yaml`. Do not cross.

## The Snapshot Handshake

Agents never communicate directly. They communicate through the snapshot table:

```
Write Agent → entity_snapshots table → Read Agent
```

This prevents the #1 failure mode in multi-agent development: **contract drift**.

- If the write agent changes the schema, the read agent's query breaks visibly.
- If the read agent expects a field the write agent hasn't populated, the publish tier degrades the page to SHELL.
- The system fails safe, not silent.

## Verification

The sprint contract defines acceptance gates. A sprint is not complete when PRs merge. It's complete when the **live site** proves the contracts are satisfied.

```bash
# Example verification sequence
# 1. Does the page render at the expected tier?
curl -s https://example.com/page | grep 'data-publish-tier'

# 2. Are internal links valid?
python scripts/validate_contracts.py --check links

# 3. Does schema emit only for qualifying pages?
python scripts/validate_contracts.py --check schema

# 4. Is the snapshot fresh?
curl -s https://example.com/api/entity/123 | jq '.updated_at'
```

## Adding a New Page Type

1. Define the page type in `contracts/page_types.yaml` with all four tiers
2. Define the enrichment stages that produce its data in `contracts/enrichment_stages.yaml`
3. Define its link rules in `contracts/link_rules.yaml`
4. Write agent builds the pipeline (writes to snapshot table)
5. Read agent builds the template (reads from snapshot table)
6. Verify agent validates against the contracts
7. Human reviews and merges

The contract is written first. The code follows. Not the reverse.

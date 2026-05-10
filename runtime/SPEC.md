# Runtime Specification

**Status:** Proposed for v0.2.0

---

## The Problem

Constitutional CMS governs what multi-agent systems are permitted to publish. The contracts declare invariants: page types, link rules, publish tiers, schema emission, ops surfaces. The agents execute against those contracts.

What the contracts do *not* govern is the working tree itself — the local filesystem where agents and humans do their work. That surface has been consistently ungoverned, and it is where coordination failures originate.

Three failure patterns have been observed repeatedly in production systems running under constitutional governance:

**1. Cross-workstream contamination.** Two agents (or an agent and a human operator) share a local checkout. Agent A's uncommitted work becomes visible to Agent B on the next file read. B commits it accidentally to their own branch.

**2. Dirty-main deploys.** A feature branch is prepared, but uncommitted experimental work remains on the local `main` checkout. A fast deploy picks up the uncommitted state and ships it to production.

**3. Contract drift.** An agent modifies a contract file as a side effect of another task. The governance system trusts the contracts as the source of truth. The drift is not caught until pages start failing validation in production.

These are not contract-layer failures. The contracts were correct. They are *runtime-layer* failures — the execution environment allowed state contamination that the contracts could not prevent because contracts do not govern filesystems.

---

## The Claim

**The working tree is an ungoverned surface.** Constitutional CMS can only govern what it can observe. It observes contract changes, publish events, and link graphs. It cannot observe filesystem state across parallel processes on the same machine.

Containerization is the minimal structural intervention that makes working-tree state governable. By isolating each workstream into its own ephemeral execution environment with a read-only view of the canonical contracts, the three failure patterns above become *structurally impossible* rather than merely *prohibited by discipline*.

Discipline fails at 11pm. Structure does not.

---

## Three Invariants

A constitutional runtime implementation MUST satisfy three invariants. These are the runtime's equivalent of the `link_rules` and `publish_tier` contracts: declarative, enforceable, and falsifiable by inspection.

### Invariant 1 — Contracts Mount Read-Only

The contract directory (typically `contracts/`) MUST be mounted into the container as a read-only filesystem. Agents executing inside the container MUST NOT be able to modify contract files in their local view, even with elevated privileges within the container.

**Rationale:** Contract changes must go through a separate governance flow. Any runtime that allows in-workstream contract modification re-introduces the contract-drift failure mode the isolation was designed to prevent.

**Verification:** A validation hook SHOULD attempt to write to a contract file during container startup and fail the container if the write succeeds.

### Invariant 2 — Working Directories Are Ephemeral

The container's working directory MUST be ephemeral. It MUST be initialized from a clean clone of the canonical repository at a specific ref (typically the tip of `main`). It MUST be discarded when the container exits.

**Rationale:** Persistent local state across container invocations re-introduces the dirty-worktree failure mode. Ephemerality is the structural guarantee that every workstream begins from a known-good state.

**Verification:** Container images SHOULD NOT mount persistent volumes at the working directory path. If caching is required (e.g. dependency caches), it MUST be isolated to paths outside the working tree.

### Invariant 3 — Publish Gates Run In The Build

Contract validation, schema emission, heading semantics, link integrity, publish-tier checks — the full set of gates declared by the contracts — MUST run as part of the container build or execution step. The build MUST fail non-zero if any gate fails.

**Rationale:** A validation step that can be skipped is not a gate. By running gates inside the container, the artifact that exits the container is by definition contract-compliant. Downstream systems (CI, deploy, edge) MAY trust the exit status without re-validating.

**Verification:** The container's exit contract SHOULD be `exit 0` if and only if all gates passed. Any other exit code indicates failure and MUST prevent publication.

---

## The Container Contract

A constitutional runtime container is defined by four properties:

**Input:** A canonical repository URL, a target ref (branch or commit SHA), and the workstream's intended change (prompt, task specification, or agent instruction).

**Environment:** Clean clone of the repository at the target ref. Contracts mounted read-only. Tooling (language runtimes, agent runtimes, validators) installed. No network access except to endpoints declared in the runtime manifest.

**Output:** Either a commit SHA pushed to a feature branch on the canonical origin, or a non-zero exit code with structured error output describing which gate failed.

**Lifecycle:** Start → clone → branch → work → validate → push → exit. Each step is atomic. The container does not resume from a previous state.

---

## Lifecycle Detail

1. **Start.** Runtime receives input (repo, ref, task). Image is pulled or built.
2. **Clone.** Fresh clone of canonical repository at specified ref. This is the only source of working-tree state.
3. **Branch.** Feature branch created with enforced naming (typically `agent/{workstream}/{task-id}`).
4. **Work.** Agent or human operator executes the task inside the container. All file modifications happen within the ephemeral working tree.
5. **Validate.** Every gate declared by the contracts runs. Heading semantics, link rules, publish tier, schema, and any runtime-specific gates (e.g. contract-modification detection) execute in sequence. Any failure halts the lifecycle.
6. **Push.** On validation success, the feature branch is pushed to the canonical origin. The commit SHA is emitted as structured output.
7. **Exit.** Container terminates. Working directory is discarded.

No step in this lifecycle depends on state from a previous invocation. Every run is independent.

---

## What This Is Not

**This is not a Docker specification.** Docker is one valid implementation of the runtime contract. Podman, Firecracker, Nix shells, and Cloudflare Worker isolates are also valid if they satisfy the three invariants. The contract is implementation-agnostic.

**This is not a deployment specification.** The runtime contract covers the workstream execution environment. How the resulting commit is merged, built into a production image, or deployed to edge infrastructure is out of scope and governed by separate contracts.

**This is not a sandbox for untrusted code.** Constitutional runtimes assume the agents and operators inside the container are trusted to execute the task. The isolation is about preventing *accidental* contamination across workstreams, not about containing *malicious* behavior. Sandboxing untrusted code requires additional controls beyond this spec.

---

## Prior Art

**Cloudflare emdash** sandboxes *plugins* in Worker isolates. The scope is the plugin surface — third-party extensions to a CMS. The constitutional runtime scope is *entire workstreams* — the whole environment in which an agent or operator modifies the governed system. emdash's isolation model is aligned with this spec but operates at a narrower boundary.

**Standard CI containers** (GitHub Actions, CircleCI, GitLab CI) satisfy Invariant 2 (ephemerality) but typically do not satisfy Invariant 1 — read-only contracts are not enforced; CI runners can modify any file they can read. A constitutional runtime is a stricter superset of standard CI.

**Nix shells and dev containers** satisfy parts of Invariant 2 but generally expose the full local filesystem, violating Invariant 1. They are complements to, not replacements for, the constitutional runtime spec.

**Anthropic's Harness** addresses session continuity for agents operating on codebases. The constitutional runtime addresses environmental isolation across simultaneous workstreams. The two are orthogonal: a harness manages one agent's memory over time; a runtime manages many workstreams' state across space.

---

## Reference Implementation

A reference implementation of this specification is planned for a subsequent release. It will include:

- A Dockerfile establishing the read-only contract mount pattern
- A docker-compose example demonstrating multi-workstream orchestration
- A validation hook library implementing the gate registration pattern
- A lifecycle wrapper script handling the clone → push → exit flow

The reference implementation is not prescriptive. It is provided as a working example that adopters can fork or replace with their preferred container technology.

---

## Versioning and Compatibility

This specification is versioned independently from the core Constitutional CMS contract spec. Runtime implementations SHOULD declare the spec version they target in their manifest. Contract-level changes do not require runtime changes; runtime-level changes do not require contract changes.

Changes to this specification follow semver:

- **PATCH** — clarifications, typo fixes, non-normative additions
- **MINOR** — new optional invariants, new MAY-level recommendations, new guidance sections
- **MAJOR** — changes to the three MUST-level invariants

---

## Contributing

This specification welcomes adoption, critique, and alternative implementations. Proposed changes follow the same constitutional discipline the repository advocates: a feature branch, a pull request, a statement of what novel property the change introduces or what existing property it clarifies.

The specification is more valuable when multiple independent runtime implementations exist and remain interoperable. Forks that maintain the three invariants are welcome contributions to the category, not competitors to the reference work.

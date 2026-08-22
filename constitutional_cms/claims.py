#!/usr/bin/env python3
"""Claim Gate v0.1 — ClaimBundleV0_1 + ClaimReceiptV0_1 (DRAFT, pre-ratification).

The portable claim-verification primitive:

* A **ClaimBundle** is the frozen, hashed, Ed25519-signed core. Volatile facts
  (verification results, current status, supersession) are FORBIDDEN inside it.
* A **ClaimReceipt** is the volatile verification record that QUOTES the
  bundle by ``bundle_hash``. A receipt attests INTEGRITY and policy
  conformance of the bundle — never "truth".

Canonicalization is the house procedure from ``docs/CANONICAL_JSON.md`` and is
imported from :mod:`constitutional_cms.evaluator` — one code path, no drift.

Ed25519 requires the optional extra::

    pip install "constitutional-cms[claims]"

The base install stays lean (PyYAML + jsonschema); every signing or verifying
entry point raises a clear error naming the extra when ``cryptography`` is
absent. Private key material is loaded from a file path (or an environment
variable holding a path) and is never printed, logged, or returned.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from . import __version__
from .evaluator import (
    canonical_json,
    digest,
    evaluate,
    load_default_catalog,
    normalize_timestamp,
    parse_timestamp,
    validate_instance,
)

BUNDLE_SCHEMA = "claim_bundle_v0_1.schema.json"
RECEIPT_SCHEMA = "claim_receipt_v0_1.schema.json"

CLAIM_EVALUATOR_NAME = "constitutional-cms"

#: Default verification-policy horizon: how long a fresh receipt may stand in
#: for a verification before a strict consumer must re-verify (7 days).
DEFAULT_RECEIPT_HORIZON_SECONDS = 7 * 24 * 3600

#: Default claim time-to-live when the governing catalog declares no
#: max_age_seconds for any evidence contract of the check (7 days).
DEFAULT_CLAIM_TTL_SECONDS = 7 * 24 * 3600

#: Claim-gate reason codes (documented in docs/CLAIM_GATE.md). These extend —
#: never replace — the evaluator's existing reason-code vocabulary.
CLAIM_REASON_CODES = {
    "bundle_verified",
    "bundle_malformed",
    "hash_mismatch",
    "signature_invalid",
    "key_unknown",
    "bundle_expired",
    "expiry_mismatch",
    "claims_unmeasured",
}

#: Result-level codes for receipt verification (returned in results, never
#: stored inside a ClaimReceipt).
RECEIPT_RESULT_CODES = {
    "receipt_verified",
    "receipt_malformed",
    "receipt_hash_mismatch",
    "receipt_superseded",
    "receipt_expired",
    "bundle_mismatch",
}

KEY_PATH_ENV = "CONSTITUTIONAL_CMS_CLAIM_KEY"

_CRYPTOGRAPHY_ERROR = (
    "Ed25519 signing and verification require the optional 'claims' extra. "
    "Install it with: pip install \"constitutional-cms[claims]\""
)

#: Claim values of this shape carry an honest non-measurement and can never
#: contribute to a green receipt.
_UNMEASURED_VERDICTS = {"UNMEASURED", "NOT_APPLICABLE"}


class ClaimGateError(ValueError):
    """Operational claim-gate error (bad inputs, missing keys, bad files)."""


def _require_crypto():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as exc:  # pragma: no cover - exercised via import guard test
        raise ClaimGateError(_CRYPTOGRAPHY_ERROR) from exc
    return ed25519, serialization


@dataclass
class VerificationResult:
    """Typed outcome of a bundle or receipt verification."""

    ok: bool
    verdict: str
    reason_codes: list[str]
    detail: str
    receipt: dict[str, Any] | None = field(default=None)


def sha256_prefixed(value: Any) -> str:
    """Canonical digest of a JSON-compatible value with the mandatory prefix."""
    return f"sha256:{digest(value)}"


def bundle_signing_bytes(bundle: dict[str, Any]) -> bytes:
    """Canonical bytes covered by BOTH bundle_hash and the Ed25519 signature.

    The bundle with ``bundle_hash`` and ``signature`` omitted, canonicalized
    per docs/CANONICAL_JSON.md, encoded UTF-8.
    """
    core = {key: value for key, value in bundle.items() if key not in ("bundle_hash", "signature")}
    return canonical_json(core).encode("utf-8")


def receipt_core_bytes(receipt: dict[str, Any]) -> bytes:
    """Canonical bytes covered by receipt_hash.

    ``receipt_hash``, ``superseded``, and ``superseded_by`` are omitted:
    supersession is a volatile annotation outside the hashed core, so marking
    a receipt superseded never breaks its historical verifiability.
    """
    core = {
        key: value
        for key, value in receipt.items()
        if key not in ("receipt_hash", "superseded", "superseded_by")
    }
    return canonical_json(core).encode("utf-8")


def _hash_bytes(payload: bytes) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _claim_ttl_seconds(check: dict[str, Any], default_ttl: int) -> int:
    ages = [
        contract["max_age_seconds"]
        for contract in check.get("evidence_contracts", {}).values()
        if isinstance(contract, dict) and isinstance(contract.get("max_age_seconds"), int)
    ]
    return min(ages) if ages else default_ttl


def _rfc3339(dt) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def build_bundle(
    evidence: dict[str, Any],
    catalog: dict[str, Any] | None = None,
    *,
    issuer: str,
    generated_at: str | None = None,
    default_claim_ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
    generation_digest: str | None = None,
) -> dict[str, Any]:
    """Build an UNSIGNED ClaimBundle core from evidence + catalog inputs.

    Honest scope: this builds only what the current reference evaluator can
    attest — one claim per catalog check, whose value is the check's verdict
    and reason code. It does not invent claims about the world; UNMEASURED
    verdicts are carried honestly and can never yield a green receipt.

    The returned dict deliberately lacks ``bundle_hash`` and ``signature``
    (and therefore does not yet validate against ClaimBundleV0_1); pass it to
    :func:`sign_bundle` to freeze it. ``generated_at`` defaults to the
    evaluation clock (the evidence ``collected_at``) so bundle identity is
    deterministic — the runtime clock never silently changes identity.
    """
    catalog = catalog if catalog is not None else load_default_catalog()
    receipt = evaluate(catalog, evidence)  # validates catalog + evidence

    observed_at = receipt["evaluated_at"]
    observed_time = parse_timestamp(observed_at)
    assert observed_time is not None
    evidence_digest = f"sha256:{receipt['evaluation_context']['evidence_digest']}"
    checks_by_id = {check["check_id"]: check for check in catalog["checks"]}

    claims: list[dict[str, Any]] = []
    for item in receipt["checks"]:
        check = checks_by_id[item["check_id"]]
        ttl = _claim_ttl_seconds(check, default_claim_ttl_seconds)
        claims.append(
            {
                "claim_id": f"claim:{item['check_id']}",
                "value": {"verdict": item["verdict"], "reason_code": item["reason_code"]},
                "authority": check["authority_refs"][0],
                "observed_at": observed_at,
                "valid_until": _rfc3339(observed_time + timedelta(seconds=ttl)),
                "evidence_digest": evidence_digest,
            }
        )
    if not claims:
        raise ClaimGateError("catalog produced no checks; a bundle needs at least one claim")

    bundle: dict[str, Any] = {
        "schema_version": "ClaimBundleV0_1",
        "issuer": issuer,
        "subject": {"type": "url", "id": evidence["subject"]["url"]},
        "claims": claims,
        "policy_digest": sha256_prefixed(catalog),
        "generated_at": normalize_timestamp(generated_at) if generated_at else observed_at,
        # Earliest-expiry-governs: the bundle dies when its first claim dies.
        "valid_until": min(claim["valid_until"] for claim in claims),
    }
    if generation_digest is not None:
        bundle["generation_digest"] = generation_digest
    return bundle


def generate_keypair(path: str | Path, *, key_id: str | None = None) -> dict[str, str]:
    """Generate an Ed25519 keypair; write the PRIVATE key (PEM, 0600) to ``path``.

    Returns only PUBLIC material: ``{"key_id", "alg", "public_key"}`` — a
    ready keys.json entry. The private key is never returned or printed.
    """
    ed25519, serialization = _require_crypto()
    import hashlib

    private_key = ed25519.Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.touch(mode=0o600, exist_ok=True)
    destination.write_bytes(pem)
    try:
        destination.chmod(0o600)
    except OSError:  # pragma: no cover - platform-specific
        pass

    raw_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    derived_id = key_id or f"key-{hashlib.sha256(raw_public).hexdigest()[:8]}"
    return {
        "key_id": derived_id,
        "alg": "Ed25519",
        "public_key": base64.b64encode(raw_public).decode("ascii"),
    }


def _load_private_key(key_path: str | Path | None):
    ed25519, serialization = _require_crypto()
    path = key_path or os.environ.get(KEY_PATH_ENV)
    if not path:
        raise ClaimGateError(
            f"no signing key: pass a key path or set {KEY_PATH_ENV} to a private-key file path"
        )
    try:
        pem = Path(path).read_bytes()
    except OSError as exc:
        raise ClaimGateError(f"could not read signing key file: {exc}") from exc
    try:
        private_key = serialization.load_pem_private_key(pem, password=None)
    except (ValueError, TypeError) as exc:
        raise ClaimGateError("signing key file is not a readable PEM Ed25519 private key") from exc
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ClaimGateError("signing key is not Ed25519")
    return private_key


def sign_bundle(
    bundle: dict[str, Any],
    *,
    key_id: str,
    key_path: str | Path | None = None,
) -> dict[str, Any]:
    """Freeze a bundle core: compute bundle_hash and Ed25519 signature.

    The signature covers exactly the canonical bytes ``bundle_hash`` covers
    (the bundle with ``bundle_hash`` and ``signature`` omitted). Returns a new
    dict that validates against ClaimBundleV0_1; the input is not mutated.
    The private key is loaded from ``key_path`` or the
    ``CONSTITUTIONAL_CMS_CLAIM_KEY`` environment variable (a file path, never
    a value) and is never echoed.
    """
    private_key = _load_private_key(key_path)
    payload = bundle_signing_bytes(bundle)
    signed = {key: value for key, value in bundle.items() if key not in ("bundle_hash", "signature")}
    signed["bundle_hash"] = _hash_bytes(payload)
    signed["signature"] = {
        "alg": "Ed25519",
        "key_id": key_id,
        "sig": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }
    validate_instance(signed, BUNDLE_SCHEMA, "ClaimBundleV0_1")
    return signed


def load_keys(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load a keys document (the /.well-known/constitutional-cms/keys.json shape)."""
    if isinstance(source, dict):
        document = source
    else:
        try:
            document = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ClaimGateError(f"could not load keys file: {exc}") from exc
    keys = document.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ClaimGateError("keys document must contain a non-empty 'keys' array")
    return document


def _public_key_for(keys_document: dict[str, Any], key_id: str):
    ed25519, _serialization = _require_crypto()
    for entry in keys_document["keys"]:
        if entry.get("key_id") == key_id and entry.get("alg") == "Ed25519":
            try:
                raw = base64.b64decode(entry["public_key"], validate=True)
                return ed25519.Ed25519PublicKey.from_public_bytes(raw)
            except (KeyError, ValueError) as exc:
                raise ClaimGateError(f"keys entry for {key_id!r} is malformed") from exc
    return None


def _receipt_id_for(bundle_hash: str, verified_at: str, evaluator_version: str) -> str:
    seed = {"bundle_hash": bundle_hash, "verified_at": verified_at, "evaluator_version": evaluator_version}
    return f"cr_{digest(seed)[:16]}"


def _make_receipt(
    bundle_hash: str,
    verdict: str,
    reason_codes: list[str],
    verified_at: str,
    valid_until: str,
    bindings: dict[str, Any] | None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": "ClaimReceiptV0_1",
        "receipt_id": _receipt_id_for(bundle_hash, verified_at, __version__),
        "bundle_hash": bundle_hash,
        "verdict": verdict,
        "reason_codes": reason_codes,
        "verified_at": verified_at,
        "valid_until": valid_until,
        "evaluator": {"name": CLAIM_EVALUATOR_NAME, "version": __version__},
        "superseded": False,
        "superseded_by": None,
    }
    if bindings:
        receipt["bindings"] = bindings
    receipt["receipt_hash"] = _hash_bytes(receipt_core_bytes(receipt))
    validate_instance(receipt, RECEIPT_SCHEMA, "ClaimReceiptV0_1")
    return receipt


def verify_bundle(
    bundle: dict[str, Any],
    keys: str | Path | dict[str, Any],
    *,
    as_of: str | None = None,
    horizon_seconds: int = DEFAULT_RECEIPT_HORIZON_SECONDS,
    bindings: dict[str, Any] | None = None,
) -> VerificationResult:
    """Verify a signed ClaimBundle fully offline and emit a ClaimReceipt.

    Verifies INTEGRITY (schema, bundle_hash, Ed25519 signature against the
    keys document) and POLICY conformance (earliest-expiry-governs, expiry,
    honest measurement) — never truth. Fail closed: an unknown key_id or any
    integrity break is a refusal, and refusals carry typed reason codes.

    ``as_of`` pins the verification clock (defaults to the current UTC time).
    The emitted receipt expires at min(bundle valid_until, as_of + horizon),
    never before ``verified_at``.
    """
    from datetime import datetime, timezone

    verified_time = parse_timestamp(normalize_timestamp(as_of)) if as_of else datetime.now(timezone.utc).replace(microsecond=0)
    assert verified_time is not None
    verified_at = _rfc3339(verified_time)

    def refuse(verdict: str, codes: list[str], detail: str, bundle_hash: str | None) -> VerificationResult:
        receipt = None
        if bundle_hash:
            receipt = _make_receipt(bundle_hash, verdict, codes, verified_at, receipt_valid_until, bindings)
        return VerificationResult(False, verdict, codes, detail, receipt)

    quoted_hash = bundle.get("bundle_hash") if isinstance(bundle, dict) else None
    if not (isinstance(quoted_hash, str) and len(quoted_hash) == 71 and quoted_hash.startswith("sha256:")):
        quoted_hash = None

    valid_until_time = parse_timestamp(bundle.get("valid_until")) if isinstance(bundle, dict) else None
    horizon_time = verified_time + timedelta(seconds=horizon_seconds)
    receipt_valid_until_time = min(valid_until_time, horizon_time) if valid_until_time else horizon_time
    if receipt_valid_until_time < verified_time:
        receipt_valid_until_time = verified_time
    receipt_valid_until = _rfc3339(receipt_valid_until_time)

    # 1. Schema: a malformed bundle is refused, not guessed at.
    try:
        validate_instance(bundle, BUNDLE_SCHEMA, "ClaimBundleV0_1")
    except (ValueError, TypeError) as exc:
        return refuse("FAIL", ["bundle_malformed"], f"bundle does not validate: {exc}", quoted_hash)

    # 2. Hash integrity: one changed byte fails here.
    payload = bundle_signing_bytes(bundle)
    computed_hash = _hash_bytes(payload)
    if computed_hash != bundle["bundle_hash"]:
        return refuse(
            "FAIL",
            ["hash_mismatch"],
            "bundle_hash does not match the canonical bytes of the bundle core",
            bundle["bundle_hash"],
        )

    # 3. Signature: unknown key fails CLOSED; bad signature is a refusal.
    keys_document = load_keys(keys)
    key_id = bundle["signature"]["key_id"]
    public_key = _public_key_for(keys_document, key_id)
    if public_key is None:
        return refuse("FAIL", ["key_unknown"], f"no Ed25519 key {key_id!r} in the keys document", computed_hash)
    try:
        public_key.verify(base64.b64decode(bundle["signature"]["sig"]), payload)
    except Exception:
        return refuse("FAIL", ["signature_invalid"], "Ed25519 signature does not verify over the canonical bytes", computed_hash)

    # 4. Earliest-expiry-governs is LAW, not prose.
    earliest_claim = min(claim["valid_until"] for claim in bundle["claims"])
    if bundle["valid_until"] != earliest_claim:
        return refuse(
            "FAIL",
            ["expiry_mismatch"],
            f"bundle valid_until {bundle['valid_until']} must equal the earliest claim valid_until {earliest_claim}",
            computed_hash,
        )

    # 5. Expiry (inclusive boundary: expired when as_of >= valid_until).
    assert valid_until_time is not None
    if verified_time >= valid_until_time:
        return refuse("FAIL", ["bundle_expired"], f"bundle expired at {bundle['valid_until']}", computed_hash)

    # 6. Honest measurement: all-UNMEASURED evidence is never a green receipt.
    def _is_unmeasured(claim: dict[str, Any]) -> bool:
        value = claim["value"]
        return isinstance(value, dict) and value.get("verdict") in _UNMEASURED_VERDICTS

    if all(_is_unmeasured(claim) for claim in bundle["claims"]):
        receipt = _make_receipt(computed_hash, "UNMEASURED", ["claims_unmeasured"], verified_at, receipt_valid_until, bindings)
        return VerificationResult(
            False,
            "UNMEASURED",
            ["claims_unmeasured"],
            "every claim carries an unmeasured verdict; integrity holds but nothing is attested",
            receipt,
        )

    receipt = _make_receipt(computed_hash, "PASS", ["bundle_verified"], verified_at, receipt_valid_until, bindings)
    return VerificationResult(True, "PASS", ["bundle_verified"], "bundle integrity and policy conformance verified", receipt)


def supersede_receipt(old_receipt: dict[str, Any], superseded_by: str) -> dict[str, Any]:
    """Return a COPY of ``old_receipt`` annotated as superseded.

    Never-overwrite law: the hashed core (everything except ``receipt_hash``,
    ``superseded``, ``superseded_by``) is untouched, so the returned record
    still verifies historically while refusing to represent current state.
    """
    annotated = dict(old_receipt)
    annotated["superseded"] = True
    annotated["superseded_by"] = superseded_by
    validate_instance(annotated, RECEIPT_SCHEMA, "ClaimReceiptV0_1")
    return annotated


def verify_receipt(
    receipt: dict[str, Any],
    bundle: dict[str, Any] | None = None,
    *,
    current: bool = True,
    as_of: str | None = None,
) -> VerificationResult:
    """Verify a ClaimReceipt's integrity; optionally check it quotes ``bundle``.

    ``current=True`` (the default) asks "may this receipt represent current
    state?" — a superseded or expired receipt is refused. ``current=False``
    is the historical question: integrity only, supersession and expiry
    allowed. Verifying a receipt never verifies the bundle itself; a strict
    consumer runs :func:`verify_bundle` for that.
    """
    from datetime import datetime, timezone

    now = parse_timestamp(normalize_timestamp(as_of)) if as_of else datetime.now(timezone.utc)

    try:
        validate_instance(receipt, RECEIPT_SCHEMA, "ClaimReceiptV0_1")
    except (ValueError, TypeError) as exc:
        return VerificationResult(False, "FAIL", ["receipt_malformed"], f"receipt does not validate: {exc}")

    if _hash_bytes(receipt_core_bytes(receipt)) != receipt["receipt_hash"]:
        return VerificationResult(
            False, "FAIL", ["receipt_hash_mismatch"], "receipt_hash does not match the canonical receipt core"
        )

    if bundle is not None:
        # bundle_mismatch trigger (normative): the receipt's quoted bundle_hash
        # differs from the hash RECOMPUTED over the presented bundle's core
        # bytes. The presented bundle's own stated bundle_hash field is ignored
        # here — its integrity belongs to verify_bundle.
        recomputed = _hash_bytes(bundle_signing_bytes(bundle))
        if recomputed != receipt["bundle_hash"]:
            return VerificationResult(
                False, "FAIL", ["bundle_mismatch"], "receipt quotes a different bundle_hash than the presented bundle's recomputed hash"
            )

    if current:
        if receipt["superseded"]:
            by = receipt["superseded_by"]
            return VerificationResult(
                False,
                "FAIL",
                ["receipt_superseded"],
                f"receipt is superseded by {by!r} and cannot represent current state",
            )
        valid_until = parse_timestamp(receipt["valid_until"])
        # Same inclusive boundary as bundles: expired when as_of >= valid_until.
        if valid_until is not None and now is not None and now >= valid_until:
            return VerificationResult(
                False, "FAIL", ["receipt_expired"], f"receipt expired at {receipt['valid_until']}"
            )

    scope = "current state" if current else "historical record"
    return VerificationResult(True, "PASS", ["receipt_verified"], f"receipt integrity verified as {scope}")

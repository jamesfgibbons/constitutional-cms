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
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import __version__
from .evaluator import (
    canonical_json,
    digest,
    evaluate,
    load_default_catalog,
    validate_instance,
)

BUNDLE_SCHEMA = "claim_bundle_v0_1.schema.json"
RECEIPT_SCHEMA = "claim_receipt_v0_1.schema.json"
KEYS_SCHEMA = "claim_keys_v0_1.schema.json"

CLAIM_EVALUATOR_NAME = "constitutional-cms"

#: Default verification-policy horizon: how long a fresh receipt may stand in
#: for a verification before a strict consumer must re-verify (7 days).
DEFAULT_RECEIPT_HORIZON_SECONDS = 7 * 24 * 3600

#: Bound on the verification-policy horizon. A horizon is a policy dial, not an
#: arbitrary integer: unbounded values overflow date arithmetic in every
#: implementation and mean nothing as policy. 10 years, in seconds.
MAX_RECEIPT_HORIZON_SECONDS = 10 * 365 * 24 * 3600

#: Interoperable-integer range (IEEE-754 double exact integers). A JSON number
#: outside it does not survive a round trip through implementations that parse
#: numbers as doubles, so v0.1 refuses it rather than hashing bytes that another
#: verifier cannot reproduce.
MAX_SAFE_INTEGER = 2**53 - 1

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
    "issuer_mismatch",
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


#: Quoted-hash surface form. Every outer hash in v0.1 carries this exact shape;
#: anything else is refused before it is used or copied into a receipt.
SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")

_RFC3339 = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})$"
)


class ClaimGateError(ValueError):
    """Operational claim-gate error (bad inputs, missing keys, bad files)."""


def _split_rfc3339(value: Any) -> tuple[datetime, str] | None:
    """Strict RFC 3339 parse → (UTC datetime truncated to the second, fraction digits).

    ``format: date-time`` is NOT enforced by jsonschema in this project's
    dependency set (no ``rfc3339-validator``), and the schema pattern is only
    a shape, so ``2026-13-45T99:99:99Z`` and the leap second
    ``2026-06-30T23:59:60Z`` both pass validation. Real parse-validation lives
    here so those become typed refusals instead of exceptions.
    """
    if not isinstance(value, str):
        return None
    match = _RFC3339.match(value)
    if match is None:
        return None
    year, month, day, hour, minute, second = (int(match.group(index)) for index in range(1, 7))
    if second > 59:
        # Leap seconds are not representable in POSIX-style civil time; refuse
        # rather than silently move the instant.
        return None
    offset = match.group(8)
    try:
        if offset == "Z":
            moment = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        else:
            sign = 1 if offset[0] == "+" else -1
            delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[4:6])) * sign
            moment = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc) - delta
    except (ValueError, OverflowError):
        return None
    return moment, match.group(7) or ""


def parse_instant(value: Any) -> datetime | None:
    """Return the UTC instant ``value`` names, or None when it names none.

    Sub-second digits are truncated to microseconds (the resolution of
    :class:`datetime`); use :func:`instant_key` when the comparison must be
    exact at any precision.
    """
    parsed = _split_rfc3339(value)
    if parsed is None:
        return None
    moment, fraction = parsed
    if not fraction:
        return moment
    return moment + timedelta(microseconds=int((fraction + "000000")[:6]))


def instant_key(value: Any) -> tuple[datetime, Decimal] | None:
    """Exact, order-preserving comparison key for an RFC 3339 timestamp.

    Timestamps are compared as INSTANTS, never as strings. The schema permits
    fractional seconds, and ``.`` (0x2E) sorts before ``Z`` (0x5A), so lexical
    order is not chronological order: ``…12:00:00.999999Z`` sorts BEFORE
    ``…12:00:00Z`` as a string while being LATER as an instant.
    """
    parsed = _split_rfc3339(value)
    if parsed is None:
        return None
    moment, fraction = parsed
    return moment, Decimal("0." + fraction) if fraction else Decimal(0)


def load_json_strict(text: str, label: str) -> Any:
    """Parse JSON, refusing duplicate object members.

    RFC 8259 leaves duplicate members undefined and implementations disagree
    (Python and JavaScript keep the LAST, some keep the first, some error). A
    document whose meaning depends on that choice cannot be independently
    verified, so v0.1 refuses it at the door.
    """

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _value in pairs:
            if key in seen:
                raise ValueError(f"duplicate JSON object member {key!r}")
            seen.add(key)
        return dict(pairs)

    try:
        return json.loads(text, object_pairs_hook=object_pairs_hook)
    except ValueError as exc:
        raise ClaimGateError(f"could not parse {label} as canonical-safe JSON: {exc}") from exc


def non_interoperable_number(value: Any, path: str = "<root>") -> str | None:
    """Return a description of the first non-interoperable number, or None.

    Canonicalization collapses integral floats (``1.0`` → ``1``) and emits
    arbitrary-precision integers as full decimal literals, so two conformant
    implementations can produce different bytes — and therefore different
    hashes — for the same parsed document. v0.1 MUST-rejects both shapes.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            found = non_interoperable_number(child, f"{path}.{key}")
            if found is not None:
                return found
        return None
    if isinstance(value, list):
        for index, child in enumerate(value):
            found = non_interoperable_number(child, f"{path}[{index}]")
            if found is not None:
                return found
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        return f"{path}: JSON floats are not interoperable in v0.1 (canonicalization collapses 1.0 to 1)"
    if isinstance(value, int) and abs(value) > MAX_SAFE_INTEGER:
        return f"{path}: integer magnitude exceeds the interoperable range (2^53-1)"
    return None


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


def _normalize_instant(value: Any) -> str:
    """Canonical ``…Z`` spelling of an RFC 3339 instant; raises when it is not one."""
    moment = parse_instant(value)
    if moment is None:
        raise ClaimGateError(f"Invalid RFC 3339 timestamp: {value!r}")
    return _rfc3339(moment)


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
    observed_time = parse_instant(observed_at)
    if observed_time is None:
        raise ClaimGateError(f"evaluation clock {observed_at!r} is not an RFC 3339 instant")
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
        "generated_at": _normalize_instant(generated_at) if generated_at else observed_at,
        # Earliest-expiry-governs: the bundle dies when its first claim dies.
        # The minimum is taken over INSTANTS, never over the lexical forms.
        "valid_until": min(claims, key=lambda claim: instant_key(claim["valid_until"]))["valid_until"],
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
    if not isinstance(bundle, dict):
        raise ClaimGateError("a bundle core must be a JSON object")
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
    # Refuse to emit what no conformant verifier will accept. This binds the
    # producer to the same structural law as the verifier; it is not a security
    # control (an attacker signs with a raw Ed25519 library, which is exactly
    # how the adversarial tests build their specimens).
    defect = _structural_defect(signed)
    if defect is not None:
        raise ClaimGateError(f"refusing to sign a bundle no verifier will accept: {defect}")
    return signed


def load_keys(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """Load and VALIDATE a keys document (the ``keys.json`` shape).

    The keys document is the verifier's own configuration, not the artifact
    under test, so every problem here is an operational refusal
    (:class:`ClaimGateError` → CLI exit 2), never a typed verdict about the
    bundle. It is validated against ClaimKeysV0_1 — ``schema_version``,
    ``issuer``, and a non-empty ``keys`` array of ``{key_id, alg, public_key}``
    — and a document carrying two entries with the same ``key_id`` is refused
    FAIL CLOSED: first-match lookup would otherwise let document ORDER decide
    the verdict, so an attacker who can append one entry could flip it.
    """
    if isinstance(source, dict):
        document = source
    else:
        try:
            text = Path(source).read_text(encoding="utf-8")
        except OSError as exc:
            raise ClaimGateError(f"could not load keys file: {exc}") from exc
        document = load_json_strict(text, "keys document")
    try:
        validate_instance(document, KEYS_SCHEMA, "ClaimKeysV0_1")
    except (ValueError, TypeError) as exc:
        raise ClaimGateError(f"keys document is malformed: {exc}") from exc
    seen: set[str] = set()
    for entry in document["keys"]:
        key_id = entry["key_id"]
        if key_id in seen:
            raise ClaimGateError(
                f"keys document contains duplicate key_id {key_id!r}; refusing fail-closed "
                "(with a duplicate, document order — not the key — decides the verdict)"
            )
        seen.add(key_id)
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


def _verification_clock(as_of: str | None) -> datetime:
    """The explicit verification clock. An unusable ``as_of`` is operational."""
    if as_of is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    moment = parse_instant(as_of)
    if moment is None:
        raise ClaimGateError(f"as_of {as_of!r} is not an RFC 3339 instant")
    return moment


def _checked_horizon(horizon_seconds: Any) -> int:
    """Bound the verification-policy horizon; an unbounded dial is operational."""
    if isinstance(horizon_seconds, bool) or not isinstance(horizon_seconds, int):
        raise ClaimGateError("horizon_seconds must be an integer number of seconds")
    if not 0 <= horizon_seconds <= MAX_RECEIPT_HORIZON_SECONDS:
        raise ClaimGateError(
            f"horizon_seconds must be between 0 and {MAX_RECEIPT_HORIZON_SECONDS} "
            f"(10 years); got {horizon_seconds}"
        )
    return horizon_seconds


def _structural_defect(bundle: dict[str, Any]) -> str | None:
    """Bundle rules that JSON Schema cannot express. Returns a detail or None.

    JSON Schema pins shape; these pin meaning:

    * ``claim_id`` uniqueness — consumers key claims by ``claim_id``, so two
      entries sharing one make the bundle's meaning depend on which the
      consumer keeps (a PASS and a FAIL under the same id must never verify).
    * real timestamps — ``format: date-time`` is not enforced here, so the
      pattern alone admits ``2026-13-45T99:99:99Z`` and leap seconds.
    * interoperable numbers — see :func:`non_interoperable_number`.
    """
    seen: set[str] = set()
    for claim in bundle["claims"]:
        claim_id = claim["claim_id"]
        if claim_id in seen:
            return (
                f"duplicate claim_id {claim_id!r}: consumers key claims by claim_id, "
                "so a bundle MUST carry each claim_id at most once"
            )
        seen.add(claim_id)
        for member in ("observed_at", "valid_until"):
            if instant_key(claim[member]) is None:
                return f"claim {claim_id!r} {member} {claim[member]!r} is not a real RFC 3339 UTC instant"
    for member in ("generated_at", "valid_until"):
        if instant_key(bundle[member]) is None:
            return f"bundle {member} {bundle[member]!r} is not a real RFC 3339 UTC instant"
    return non_interoperable_number(bundle, "bundle")


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
    ISSUER'S keys document) and POLICY conformance (issuer binding,
    earliest-expiry-governs, expiry, honest measurement) — never truth. Fail
    closed: an unknown key_id or any integrity break is a refusal, and
    refusals carry typed reason codes.

    TOTAL over artifacts: no bundle value, however malformed, escapes as an
    exception — every one becomes a typed refusal. The only exception this
    function raises is :class:`ClaimGateError`, and only for VERIFIER-side
    inputs (an unusable ``as_of`` or ``horizon_seconds``, a missing or
    malformed keys document); those are operational, not verdicts.

    ``as_of`` pins the verification clock (defaults to the current UTC time).
    The emitted receipt expires at min(bundle valid_until, as_of + horizon),
    never before ``verified_at``.
    """
    # Verifier-side inputs are resolved FIRST and fail operationally.
    horizon_seconds = _checked_horizon(horizon_seconds)
    verified_time = _verification_clock(as_of)
    verified_at = _rfc3339(verified_time)
    keys_document = load_keys(keys)

    quoted_hash = bundle.get("bundle_hash") if isinstance(bundle, dict) else None
    if not (isinstance(quoted_hash, str) and SHA256_PREFIXED.match(quoted_hash)):
        # A hash that is not in canonical surface form is never quoted into a
        # receipt: the receipt schema would refuse it and the verifier would
        # explode instead of refusing the bundle.
        quoted_hash = None

    valid_until_time = parse_instant(bundle.get("valid_until")) if isinstance(bundle, dict) else None
    horizon_time = verified_time + timedelta(seconds=horizon_seconds)
    receipt_valid_until_time = min(valid_until_time, horizon_time) if valid_until_time else horizon_time
    if receipt_valid_until_time < verified_time:
        receipt_valid_until_time = verified_time
    receipt_valid_until = _rfc3339(receipt_valid_until_time)

    def refuse(verdict: str, codes: list[str], detail: str, bundle_hash: str | None) -> VerificationResult:
        receipt = None
        if bundle_hash:
            receipt = _make_receipt(bundle_hash, verdict, codes, verified_at, receipt_valid_until, bindings)
        return VerificationResult(False, verdict, codes, detail, receipt)

    try:
        return _verify_bundle_checks(
            bundle,
            keys_document,
            verified_time=verified_time,
            quoted_hash=quoted_hash,
            refuse=refuse,
            verified_at=verified_at,
            receipt_valid_until=receipt_valid_until,
            bindings=bindings,
        )
    except ClaimGateError:
        raise
    except Exception as exc:  # totality: never a traceback, always a verdict
        return VerificationResult(
            False,
            "FAIL",
            ["bundle_malformed"],
            f"bundle could not be processed: {type(exc).__name__}: {exc}",
            None,
        )


def _verify_bundle_checks(
    bundle: dict[str, Any],
    keys_document: dict[str, Any],
    *,
    verified_time: datetime,
    quoted_hash: str | None,
    refuse,
    verified_at: str,
    receipt_valid_until: str,
    bindings: dict[str, Any] | None,
) -> VerificationResult:
    """The normative check sequence (docs/CLAIM_GATE.md). First failure wins."""
    # 1. Schema + the structural rules JSON Schema cannot express.
    try:
        validate_instance(bundle, BUNDLE_SCHEMA, "ClaimBundleV0_1")
    except (ValueError, TypeError) as exc:
        return refuse("FAIL", ["bundle_malformed"], f"bundle does not validate: {exc}", quoted_hash)
    defect = _structural_defect(bundle)
    if defect is not None:
        return refuse("FAIL", ["bundle_malformed"], defect, quoted_hash)

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

    # 3. Key lookup: an unknown key_id fails CLOSED.
    key_id = bundle["signature"]["key_id"]
    public_key = _public_key_for(keys_document, key_id)
    if public_key is None:
        return refuse("FAIL", ["key_unknown"], f"no Ed25519 key {key_id!r} in the keys document", computed_hash)

    # 4. Issuer binding: a key proves possession, never identity on its own.
    #    The keys document declares WHOSE keys it publishes; a bundle claiming a
    #    different issuer is refused even when the signature verifies.
    if bundle["issuer"] != keys_document["issuer"]:
        return refuse(
            "FAIL",
            ["issuer_mismatch"],
            f"bundle issuer {bundle['issuer']!r} is not the issuer this keys document "
            f"publishes keys for ({keys_document['issuer']!r})",
            computed_hash,
        )

    # 5. Ed25519 signature over the same bytes bundle_hash covers.
    try:
        public_key.verify(base64.b64decode(bundle["signature"]["sig"]), payload)
    except Exception:
        return refuse("FAIL", ["signature_invalid"], "Ed25519 signature does not verify over the canonical bytes", computed_hash)

    # 6. Earliest-expiry-governs is LAW, not prose — compared as INSTANTS.
    earliest_claim = min(bundle["claims"], key=lambda claim: instant_key(claim["valid_until"]))["valid_until"]
    if instant_key(bundle["valid_until"]) != instant_key(earliest_claim):
        return refuse(
            "FAIL",
            ["expiry_mismatch"],
            f"bundle valid_until {bundle['valid_until']} must name the same INSTANT as the "
            f"earliest claim valid_until {earliest_claim}",
            computed_hash,
        )

    # 7. Expiry (inclusive boundary: expired when as_of >= valid_until).
    if instant_key(_rfc3339(verified_time)) >= instant_key(bundle["valid_until"]):
        return refuse("FAIL", ["bundle_expired"], f"bundle expired at {bundle['valid_until']}", computed_hash)

    # 8. Honest measurement: all-UNMEASURED evidence is never a green receipt.
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


def _is_unmeasured(claim: dict[str, Any]) -> bool:
    """A claim is unmeasured iff its value is an object whose "verdict" member
    is the STRING "UNMEASURED" or "NOT_APPLICABLE". Every other value —
    including a non-string, unhashable one — counts as measured."""
    value = claim["value"]
    if not isinstance(value, dict):
        return False
    verdict = value.get("verdict")
    return isinstance(verdict, str) and verdict in _UNMEASURED_VERDICTS


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

    A v0.1 receipt is UNAUTHENTICATED: it carries no signature, so a PASS here
    means the record is internally consistent, NOT that any issuer produced
    it. See "What a v0.1 receipt does NOT prove" in docs/CLAIM_GATE.md.

    TOTAL over artifacts: any malformed receipt or bundle becomes a typed
    refusal, never an exception. Only :class:`ClaimGateError` escapes, and
    only for an unusable ``as_of`` (verifier-side, operational).
    """
    now = _verification_clock(as_of)

    try:
        return _verify_receipt_checks(receipt, bundle, current=current, now=now)
    except ClaimGateError:
        raise
    except Exception as exc:  # totality: never a traceback, always a verdict
        return VerificationResult(
            False,
            "FAIL",
            ["receipt_malformed"],
            f"receipt could not be processed: {type(exc).__name__}: {exc}",
        )


def _verify_receipt_checks(
    receipt: dict[str, Any],
    bundle: dict[str, Any] | None,
    *,
    current: bool,
    now: datetime,
) -> VerificationResult:
    """The normative receipt check sequence (docs/CLAIM_GATE.md)."""
    # 1. Schema + the structural rules JSON Schema cannot express.
    try:
        validate_instance(receipt, RECEIPT_SCHEMA, "ClaimReceiptV0_1")
    except (ValueError, TypeError) as exc:
        return VerificationResult(False, "FAIL", ["receipt_malformed"], f"receipt does not validate: {exc}")
    for member in ("verified_at", "valid_until"):
        if instant_key(receipt[member]) is None:
            return VerificationResult(
                False,
                "FAIL",
                ["receipt_malformed"],
                f"receipt {member} {receipt[member]!r} is not a real RFC 3339 UTC instant",
            )
    defect = non_interoperable_number(receipt, "receipt")
    if defect is not None:
        return VerificationResult(False, "FAIL", ["receipt_malformed"], defect)

    # 2. Receipt-hash integrity over the canonical core bytes.
    if _hash_bytes(receipt_core_bytes(receipt)) != receipt["receipt_hash"]:
        return VerificationResult(
            False, "FAIL", ["receipt_hash_mismatch"], "receipt_hash does not match the canonical receipt core"
        )

    # 3. Bundle quote check, only when a bundle is presented.
    if bundle is not None:
        # bundle_mismatch trigger (normative): the receipt's quoted bundle_hash
        # differs from the hash RECOMPUTED over the presented bundle's core
        # bytes. The presented bundle's own stated bundle_hash field is ignored
        # here — its integrity belongs to verify_bundle. A presented value that
        # is not a JSON object cannot hash to the quoted value at all.
        if not isinstance(bundle, dict):
            return VerificationResult(
                False, "FAIL", ["bundle_mismatch"], "the presented bundle is not a JSON object"
            )
        recomputed = _hash_bytes(bundle_signing_bytes(bundle))
        if recomputed != receipt["bundle_hash"]:
            return VerificationResult(
                False, "FAIL", ["bundle_mismatch"], "receipt quotes a different bundle_hash than the presented bundle's recomputed hash"
            )

    if current:
        # 4. Supersession (current-state question only).
        if receipt["superseded"]:
            by = receipt["superseded_by"]
            return VerificationResult(
                False,
                "FAIL",
                ["receipt_superseded"],
                f"receipt is superseded by {by!r} and cannot represent current state",
            )
        # 5. Expiry, same inclusive boundary as bundles: expired at as_of >= valid_until.
        if instant_key(_rfc3339(now)) >= instant_key(receipt["valid_until"]):
            return VerificationResult(
                False, "FAIL", ["receipt_expired"], f"receipt expired at {receipt['valid_until']}"
            )

    scope = "current state" if current else "historical record"
    return VerificationResult(True, "PASS", ["receipt_verified"], f"receipt integrity verified as {scope}")

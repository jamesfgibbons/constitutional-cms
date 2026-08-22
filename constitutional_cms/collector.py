#!/usr/bin/env python3
"""Public static collector: one read-only GET, normalized into EvidenceBundleV1.

This collector observes only what a single unrendered HTTP response can honestly
support (the ``public_static`` scope, ``pure_read`` mutation class). Evidence it
cannot observe — rendered accessibility audits, field Core Web Vitals, declared
configuration, private authorities — is left absent so the evaluator reports those
checks as UNMEASURED instead of guessing. Absence of evidence is never converted
into a verdict.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from typing import Any, Callable
from urllib import request
from urllib.error import HTTPError
from urllib.parse import urlparse

from . import __version__

COLLECTOR_NAME = "constitutional-cms-static-collector"
USER_AGENT = (
    f"constitutional-cms/{__version__} "
    "(+https://github.com/jamesfgibbons/constitutional-cms)"
)
DEFAULT_TIMEOUT = 20.0
MAX_BODY_BYTES = 5 * 1024 * 1024

STATIC_LIMITATIONS = [
    "Single read-only GET of the subject URL; no JavaScript rendering was performed.",
    "Rendered, crawled, declared-config, private-authority, and field observations were not collected.",
    "robots.txt was not fetched; observations.search.blocked reflects page-level controls (meta robots, X-Robots-Tag) only.",
    "observations.search.intended_indexable is a declared intent this collector cannot observe.",
]


class CollectorError(RuntimeError):
    """The subject could not be fetched at the transport level."""


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass
class DocumentFacts:
    lang: str | None = None
    canonical: str | None = None
    meta_robots: list[str] = field(default_factory=list)
    jsonld_blocks: list[str] = field(default_factory=list)


class _DocumentParser(HTMLParser):
    """Extract the static facts the check catalog can consume."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.facts = DocumentFacts()
        self._in_jsonld = False
        self._jsonld_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}
        if tag == "html" and self.facts.lang is None:
            lang = attributes.get("lang", "").strip()
            if lang:
                self.facts.lang = lang
        elif tag == "link":
            rels = attributes.get("rel", "").lower().split()
            if "canonical" in rels and self.facts.canonical is None:
                href = attributes.get("href", "").strip()
                if href:
                    self.facts.canonical = href
        elif tag == "meta":
            if attributes.get("name", "").strip().lower() == "robots":
                content = attributes.get("content", "")
                self.facts.meta_robots.extend(
                    token.strip().lower() for token in content.split(",") if token.strip()
                )
        elif tag == "script":
            if attributes.get("type", "").strip().lower() == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._jsonld_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.facts.jsonld_blocks.append("".join(self._jsonld_chunks))
            self._jsonld_chunks = []


def parse_document(html_text: str) -> DocumentFacts:
    parser = _DocumentParser()
    parser.feed(html_text)
    parser.close()
    return parser.facts


def _reject_nonfinite(_token: str) -> None:
    raise ValueError("RFC 8259 prohibits NaN and Infinity")


def jsonld_single_unescape_ok(block: str) -> bool:
    """True when the block parses as RFC 8259 JSON after exactly one HTML unescape."""
    try:
        json.loads(unescape(block), parse_constant=_reject_nonfinite)
    except ValueError:
        return False
    return True


def is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname)


def origin_for(value: str) -> str:
    parsed = urlparse(value)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def fetch(url: str, timeout: float = DEFAULT_TIMEOUT) -> FetchResult:
    """One read-only GET. HTTP error statuses are observations, not exceptions."""
    req = request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    context = ssl.create_default_context()
    try:
        response = request.urlopen(req, timeout=timeout, context=context)
    except HTTPError as error:
        response = error
    except OSError as error:  # DNS failure, refused connection, TLS failure, timeout
        raise CollectorError(f"Could not fetch {url}: {error}") from error

    with response:
        status = int(getattr(response, "status", None) or response.getcode())
        headers = {key.lower(): value for key, value in response.headers.items()}
        body = response.read(MAX_BODY_BYTES)
        if headers.get("content-encoding", "").strip().lower() == "gzip":
            try:
                body = gzip.decompress(body)
            except OSError:
                pass
        final_url = response.geturl() or url
    return FetchResult(url=url, final_url=final_url, status=status, headers=headers, body=body)


def _decode_body(result: FetchResult) -> str:
    content_type = result.headers.get("content-type", "")
    charset = None
    for token in content_type.split(";"):
        token = token.strip().lower()
        if token.startswith("charset="):
            charset = token.split("=", 1)[1].strip('"')
    for candidate in filter(None, [charset, "utf-8"]):
        try:
            return result.body.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return result.body.decode("utf-8", errors="replace")


def observe(result: FetchResult) -> dict[str, Any]:
    """Map one static response into catalog-consumable observations."""
    facts = parse_document(_decode_body(result))

    header_robots = [
        token.strip().lower()
        for token in result.headers.get("x-robots-tag", "").split(",")
        if token.strip()
    ]
    blocked = "noindex" in facts.meta_robots or "noindex" in header_robots

    observations: dict[str, Any] = {
        "http": {"status": result.status},
        "search": {
            "blocked": blocked,
            "jsonld": {"present": bool(facts.jsonld_blocks)},
        },
    }
    if facts.lang is not None:
        observations["document"] = {"lang": facts.lang}
    if facts.canonical is not None:
        observations["search"]["canonical"] = facts.canonical
    if facts.jsonld_blocks:
        observations["search"]["jsonld"]["single_unescape_rfc8259"] = all(
            jsonld_single_unescape_ok(block) for block in facts.jsonld_blocks
        )
    return observations


def collect(
    url: str,
    timeout: float = DEFAULT_TIMEOUT,
    fetch_fn: Callable[[str, float], FetchResult] | None = None,
) -> dict[str, Any]:
    """Fetch one URL and return a schema-valid EvidenceBundleV1."""
    if not is_https_url(url):
        raise CollectorError(
            f"Subject must be an absolute https:// URL (got: {url}). "
            "EvidenceBundleV1 subjects are HTTPS by contract."
        )
    result = (fetch_fn or fetch)(url, timeout)
    collected_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "EvidenceBundleV1",
        "subject": {"url": url, "canonical_origin": origin_for(url)},
        "collected_at": collected_at,
        "collector": {"name": COLLECTOR_NAME, "version": __version__},
        "scopes": [{"name": "public_static", "mutation_class": "pure_read"}],
        "observations": observe(result),
        "limitations": list(STATIC_LIMITATIONS),
        "artifact_hashes": [
            {"name": "subject_response_body", "sha256": hashlib.sha256(result.body).hexdigest()}
        ],
    }

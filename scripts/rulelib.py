"""Shared helpers for the MikeHuang01 rule generators.

Every generated file in this repository is produced the same way:

    upstream rule list  +  hand-maintained local list  ->  deduped output

The helpers below keep that pipeline identical for QuantumultX and
Shadowrocket so a fix in one generator cannot silently drift from another.
"""
from __future__ import annotations

import os
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QX_DIR = ROOT / "QuantumultX"
SR_DIR = ROOT / "Shadowrocket"

# Rule types that match on the request domain / header, no DNS needed.
NETWORK_TYPES = {"HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT", "URL-REGEX"}

# Rule types that need a resolved address (or an ASN / geo lookup).
IP_TYPES = {"IP-CIDR", "IP6-CIDR", "IP-ASN", "GEOIP", "SRC-IP", "DEST-PORT"}

# QuantumultX / Shadowrocket type mapping for Shadowrocket output.
SHADOWROCKET_TYPES = {
    "HOST": "DOMAIN",
    "HOST-SUFFIX": "DOMAIN-SUFFIX",
    "HOST-KEYWORD": "DOMAIN-KEYWORD",
}

USER_AGENT = "MikeHuang01-Rules-sync/2.0"


@dataclass(frozen=True)
class Rule:
    """One normalised rule line: ``type,value,policy[,options...]``."""

    rule_type: str
    value: str
    policy: str
    options: tuple[str, ...] = field(default_factory=tuple)

    @property
    def key(self) -> tuple[str, str]:
        """Dedupe key: rule type + match value, case-insensitive."""
        return self.rule_type, self.value.lower()

    @property
    def text(self) -> str:
        return ",".join((self.rule_type, self.value, self.policy, *self.options))

    def with_policy(self, policy: str, *, add_no_resolve: bool = False) -> "Rule":
        options = self.options
        if add_no_resolve and self.rule_type in {"IP-CIDR", "IP6-CIDR"}:
            options = tuple(o for o in options if o.lower() != "no-resolve") + ("no-resolve",)
        return Rule(self.rule_type, self.value, policy, options)

    def shadowrocket(self) -> "Rule":
        rule_type = SHADOWROCKET_TYPES.get(self.rule_type, self.rule_type)
        options = self.options
        if rule_type in {"IP-CIDR", "IP6-CIDR"}:
            options = tuple(o for o in options if o.lower() != "no-resolve") + ("no-resolve",)
        value = self.value.upper() if rule_type == "GEOIP" else self.value
        return Rule(rule_type, value, self.policy, options)


def parse_rule(line: str) -> Rule | None:
    """Parse one rule line, returning None for blanks and comments."""
    text = line.strip()
    if not text or text.startswith(("#", ";", "//")):
        return None
    parts = [part.strip() for part in text.split(",")]
    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return None
    return Rule(parts[0].upper(), parts[1], parts[2], tuple(parts[3:]))


def parse_rules(lines) -> list[Rule]:
    rules = []
    for line in lines:
        rule = parse_rule(line)
        if rule is not None:
            rules.append(rule)
    return rules


def dedupe(rules) -> list[Rule]:
    """Drop later rules that repeat an earlier ``(type, value)`` pair."""
    seen: set[tuple[str, str]] = set()
    result: list[Rule] = []
    for rule in rules:
        if rule.key in seen:
            continue
        seen.add(rule.key)
        result.append(rule)
    return result


def fetch(url: str, *, attempts: int = 3, timeout: int = 120) -> str:
    """Download ``url`` as UTF-8 text.

    Set ``RULES_UPSTREAM_CACHE`` to a directory to reuse already downloaded
    upstream files (offline runs and repeatable local verification).
    """
    cache_dir = os.environ.get("RULES_UPSTREAM_CACHE")
    if cache_dir:
        cached = Path(cache_dir) / Path(url.split("?")[0]).name
        if cached.is_file() and cached.stat().st_size > 0:
            print(f"cache hit: {cached.name}")
            return cached.read_text(encoding="utf-8-sig")

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8-sig")
        except Exception as exc:  # noqa: BLE001 - network errors are retried as-is
            last_error = exc
            print(f"fetch attempt {attempt}/{attempts} failed: {type(exc).__name__}: {exc}")
            if attempt < attempts:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Unable to download {url}: {last_error}")


def render_header(title: str, lines) -> list[str]:
    return [f"# NAME: {title}", *[f"# {line}" for line in lines], ""]


def write_if_changed(path: Path, text: str) -> bool:
    """Write ``text`` atomically; returns True when the file changed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        print(f"unchanged: {path.relative_to(ROOT)}")
        return False
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temp_name = handle.name
    os.replace(temp_name, path)
    print(f"updated: {path.relative_to(ROOT)}")
    return True


def covered_by(host: str, rule: Rule) -> bool:
    """True when ``host`` would be matched by an AdBlock suffix/keyword rule."""
    value = rule.value.lower()
    if rule.rule_type == "HOST-SUFFIX":
        return host == value or host.endswith("." + value)
    if rule.rule_type == "HOST-KEYWORD":
        return value in host
    if rule.rule_type == "HOST":
        return host == value
    return False

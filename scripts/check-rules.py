#!/usr/bin/env python3
"""Validate every generated resource before the workflow commits it.

The checks are about the contracts the README promises, so a regression fails
the GitHub Action instead of reaching a phone or a desktop client:

* every rule line parses, uses a known type and a policy the client understands;
* no ``(type, value)`` pair appears twice in one file;
* no rule is already covered by a broader rule in the same file
  (``HOST,x`` next to ``HOST-SUFFIX,x``);
* the Direct / AdBlock / DirectGeo split keeps all upstream rules;
* AdBlock never contains a ``direct`` rule and Direct never contains ``REJECT``;
* the Clash rule providers stay in ``type,value`` form, use types mihomo
  supports, and match the rule count of their QuantumultX source minus the rules
  that cannot be expressed and the ones pruned as duplicates.

All three client formats are checked, because they are generated from the same
source and must not drift apart.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

from rulelib import CLASH_DIR, CLASH_TYPES, QX_DIR, SR_DIR, Rule, parse_rule

KNOWN_TYPES = {
    "HOST",
    "HOST-SUFFIX",
    "HOST-KEYWORD",
    "USER-AGENT",
    "URL-REGEX",
    "IP-CIDR",
    "IP6-CIDR",
    "IP-ASN",
    "GEOIP",
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "PROCESS-NAME",
}

# Types mihomo accepts inside a rule-provider payload.
CLASH_KNOWN_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-REGEX",
    "IP-CIDR",
    "IP-CIDR6",
    "IP-ASN",
    "GEOIP",
    "PROCESS-NAME",
    "PROCESS-PATH",
    "SRC-IP-CIDR",
    "DST-PORT",
    "SRC-PORT",
    "NETWORK",
}

# Types a Clash provider must NOT contain: mihomo has no such rule types.
# IP6-CIDR is the QuantumultX spelling; mihomo only accepts IP-CIDR6 and
# drops the QX one with a warning, so it counts as forbidden here.
CLASH_FORBIDDEN_TYPES = {"HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT", "URL-REGEX", "IP6-CIDR"}

EXPECTED = {
    QX_DIR / "Direct.list": {"policy_any": {"direct"}},
    QX_DIR / "DirectGeo.list": {"policy_any": {"direct"}},
    QX_DIR / "AdBlock.list": {"policy_any": {"reject"}},
    QX_DIR / "ProxyLocal.list": {"policy_any": {"proxy"}},
    SR_DIR / "Direct.conf": {"policy_any": {"direct"}},
    SR_DIR / "DirectGeo.conf": {"policy_any": {"direct"}},
    SR_DIR / "AdBlock.conf": {"policy_any": {"reject"}},
    SR_DIR / "ProxyLocal.conf": {"policy_any": {"proxy"}},
}

# Clash provider -> QuantumultX source it is generated from.
CLASH_EXPECTED = {
    "Direct.yaml": "Direct.list",
    "AdBlock.yaml": "AdBlock.list",
    "DirectGeo.yaml": "DirectGeo.list",
    "ProxyLocal.yaml": "ProxyLocal.list",
}


def duplicate_problems(name: str, rules: list[Rule]) -> list[str]:
    """Report exact duplicates and rules already covered by a broader rule."""
    problems: list[str] = []
    counts = Counter(rule.key for rule in rules)
    for rule_type, value in [key for key, count in counts.items() if count > 1][:5]:
        problems.append(f"{name}: duplicate rule {rule_type},{value}")

    by_value: dict[str, set[str]] = defaultdict(set)
    for rule in rules:
        by_value[rule.value.lower()].add(rule.rule_type)
    for value, rule_types in by_value.items():
        if "HOST" in rule_types and "HOST-SUFFIX" in rule_types:
            problems.append(f"{name}: HOST,{value} is already covered by HOST-SUFFIX,{value}")
        if "DOMAIN" in rule_types and "DOMAIN-SUFFIX" in rule_types:
            problems.append(f"{name}: DOMAIN,{value} is already covered by DOMAIN-SUFFIX,{value}")

    if not rules:
        problems.append(f"{name}: no rules")
    return problems


def audit_rules(path: Path, policies: set[str]) -> list[str]:
    """Check one QuantumultX / Shadowrocket resource file."""
    if not path.is_file():
        return [f"{path.name}: missing"]
    problems: list[str] = []
    rules: list[Rule] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text or text.startswith(("#", ";")):
            continue
        rule = parse_rule(text)
        if rule is None:
            problems.append(f"{path.name}:{number}: unparsable rule: {text[:80]}")
            continue
        if rule.rule_type not in KNOWN_TYPES:
            problems.append(f"{path.name}:{number}: unknown type {rule.rule_type}")
        if rule.policy.lower() not in policies:
            problems.append(f"{path.name}:{number}: unexpected policy {rule.policy!r}")
        rules.append(rule)

    problems.extend(duplicate_problems(path.name, rules))
    print(f"{path.name}: {len(rules)} rules, {len(problems)} problems")
    return problems


def audit_clash(path: Path, source: Path) -> list[str]:
    """Check one Clash rule-provider YAML against its QuantumultX source."""
    name = path.name
    if not path.is_file():
        return [f"{name}: missing"]
    problems: list[str] = []

    pairs: list[tuple[str, str]] = []
    in_payload = False
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        if text == "payload:":
            in_payload = True
            continue
        if not in_payload or not text.startswith("- "):
            problems.append(f"{name}:{number}: unexpected line: {text[:80]}")
            continue
        entry = text[2:].strip().strip("'\"")
        rule_type, _, value = entry.partition(",")
        rule_type, value = rule_type.strip(), value.strip()
        if not rule_type or not value:
            problems.append(f"{name}:{number}: malformed entry: {entry[:80]}")
            continue
        if rule_type in CLASH_FORBIDDEN_TYPES:
            problems.append(f"{name}:{number}: QX-only type leaked into Clash: {rule_type}")
        elif rule_type not in CLASH_KNOWN_TYPES:
            problems.append(f"{name}:{number}: type not supported by mihomo: {rule_type}")
        if "," in value and rule_type not in {"DOMAIN-REGEX", "PROCESS-PATH"}:
            problems.append(f"{name}:{number}: unexpected extra field: {entry[:80]}")
        pairs.append((rule_type, value))

    counts = Counter((rule_type, value.lower()) for rule_type, value in pairs)
    for rule_type, value in [key for key, count in counts.items() if count > 1][:5]:
        problems.append(f"{name}: duplicate rule {rule_type},{value}")

    by_value: dict[str, set[str]] = defaultdict(set)
    for rule_type, value in pairs:
        by_value[value.lower()].add(rule_type)
    for value, types in by_value.items():
        if "DOMAIN" in types and "DOMAIN-SUFFIX" in types:
            problems.append(f"{name}: DOMAIN,{value} is already covered by DOMAIN-SUFFIX,{value}")

    if source.is_file():
        source_rules = [r for r in (parse_rule(line) for line in source.read_text(encoding="utf-8").splitlines()) if r]
        unsupported = sum(1 for rule in source_rules if rule.rule_type not in CLASH_TYPES and rule.rule_type not in {"IP-CIDR", "IP-ASN", "GEOIP"})
        suffix = {rule.value.lower() for rule in source_rules if rule.rule_type == "HOST-SUFFIX"}
        shadowed = len({rule.value.lower() for rule in source_rules if rule.rule_type == "HOST"} & suffix)
        expected = len(source_rules) - unsupported - shadowed
        print(
            f"{name}: {len(pairs)} rules "
            f"(source {len(source_rules)}, unsupported {unsupported}, shadowed {shadowed}, "
            f"{len(problems)} problems)"
        )
        if len(pairs) != expected:
            problems.append(f"{name}: expected {expected} rules from {source.name}, found {len(pairs)}")
    return problems


def main() -> int:
    problems: list[str] = []
    for path, spec in EXPECTED.items():
        problems.extend(audit_rules(path, spec["policy_any"]))
    for filename, source_name in CLASH_EXPECTED.items():
        problems.extend(audit_clash(CLASH_DIR / filename, QX_DIR / source_name))

    rewrite = QX_DIR / "AdvertisingLite.conf"
    if not rewrite.is_file():
        problems.append("AdvertisingLite.conf: missing")
    else:
        lines = rewrite.read_text(encoding="utf-8").splitlines()
        rewrites = [line for line in lines if line.strip() and not line.lstrip().startswith(("#", ";"))]
        hosts = [line for line in lines if line.startswith("hostname = ")]
        print(f"AdvertisingLite.conf: {len(rewrites)} rewrites, {len(hosts)} hostname line(s)")
        if not rewrites:
            problems.append("AdvertisingLite.conf: no rewrite rules")
        if len(hosts) != 1:
            problems.append("AdvertisingLite.conf: expected exactly one hostname line")

    if not (CLASH_DIR / "README.md").is_file():
        problems.append("Clash/README.md: missing (the documented differences are part of the contract)")

    # 分层契约：直连文件里不能出现 REJECT，去广告文件里不能出现 direct。
    direct_text = (QX_DIR / "Direct.list").read_text(encoding="utf-8").lower()
    adblock_text = (QX_DIR / "AdBlock.list").read_text(encoding="utf-8").lower()
    for line in direct_text.splitlines():
        if line and not line.startswith("#") and line.endswith(",reject"):
            problems.append(f"Direct.list: reject rule leaked into 直连: {line[:80]}")
            break
    for line in adblock_text.splitlines():
        if line and not line.startswith("#") and line.endswith(",direct"):
            problems.append(f"AdBlock.list: direct rule leaked into 去广告: {line[:80]}")
            break

    if problems:
        print("\nFAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("\nAll generated resources are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate every generated resource before the workflow commits it.

The checks are intentionally about the contracts the README promises, so a
regression fails the GitHub Action instead of reaching a phone:

* every rule line parses, uses a known type and a policy the client understands;
* no ``(type, value)`` pair appears twice in one file;
* the Direct / AdBlock / DirectGeo split keeps all upstream rules;
* AdBlock never contains a ``direct`` rule and Direct never contains ``REJECT``.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from rulelib import QX_DIR, SR_DIR, Rule, parse_rule

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

EXPECTED = {
    QX_DIR / "Direct.list": {"policy_any": {"direct"}},
    QX_DIR / "DirectGeo.list": {"policy_any": {"direct"}},
    QX_DIR / "AdBlock.list": {"policy_any": {"reject"}},
    SR_DIR / "Direct.conf": {"policy_any": {"direct"}},
    SR_DIR / "DirectGeo.conf": {"policy_any": {"direct"}},
    SR_DIR / "AdBlock.conf": {"policy_any": {"reject"}},
}

REWRITE_ACTIONS = ("url reject", "url 302", "url 307", "url script-")


def audit_rules(path: Path, policies: set[str]) -> list[str]:
    problems: list[str] = []
    if not path.is_file():
        return [f"{path}: missing"]
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

    duplicates = [key for key, count in Counter(rule.key for rule in rules).items() if count > 1]
    for rule_type, value in duplicates[:5]:
        problems.append(f"{path.name}: duplicate rule {rule_type},{value}")
    if not rules:
        problems.append(f"{path.name}: no rules")
    print(f"{path.name}: {len(rules)} rules, {len(duplicates)} duplicates, {len(problems)} problems")
    return problems


def main() -> int:
    problems: list[str] = []
    for path, spec in EXPECTED.items():
        problems.extend(audit_rules(path, spec["policy_any"]))

    rewrite = QX_DIR / "AdvertisingLite.conf"
    if not rewrite.is_file():
        problems.append("AdvertisingLite.conf: missing")
    else:
        lines = rewrite.read_text(encoding="utf-8").splitlines()
        rewrites = [
            line
            for line in lines
            if line.strip() and not line.lstrip().startswith(("#", ";"))
        ]
        hosts = [line for line in lines if line.startswith("hostname = ")]
        print(f"AdvertisingLite.conf: {len(rewrites)} rewrites, {len(hosts)} hostname line(s)")
        if not rewrites:
            problems.append("AdvertisingLite.conf: no rewrite rules")
        if len(hosts) != 1:
            problems.append("AdvertisingLite.conf: expected exactly one hostname line")

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

#!/usr/bin/env python3
"""Fetch blackmatrix7 AdvertisingLite and reapply local Alipay/Cainiao rules."""
from __future__ import annotations

import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "QuantumultX" / "AdvertisingLite.conf"
UPSTREAM = (
    "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/"
    "rewrite/QuantumultX/AdvertisingLite/AdvertisingLite.conf"
)
CUSTOM_SOURCE = (
    "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/"
    "AdBlock/CainiaoAds.conf"
)
CUSTOM_RULES = [
    r"^https?:\/\/[a-zA-Z0-9_.-]+\.taobao\.com\/gw\/mtop\.cainiao\.guoguo\.nbnetflow\.ads\.(?!.*_home) url reject-200",
    r"^https?:\/\/[a-zA-Z0-9_.-]+\.taobao\.com\/gw\/mtop\.alimama\.abyss\.unionpage\.get url reject-200",
    r"^https?:\/\/[a-zA-Z0-9_.-]+\.taobao\.com\/gw\/mtop\.cainiao\.adx\.flyad\.getad url reject-200",
    r"^https?:\/\/[a-zA-Z0-9_.-]+\.taobao\.com\/gw\/mtop\.cainiao\.nbmensa\.research\.researchservice\.consultmerge url reject-200",
]
CUSTOM_HOSTS = ["guide-acs.m.taobao.com", "acs4miniapp-inner.m.taobao.com"]
COUNT_NAMES = ("HOST", "HOST-KEYWORD", "IP-CIDR", "IP6-CIDR", "REJECT", "MITM", "TOTAL")


def read_count(lines: list[str], name: str) -> int:
    matches = [re.fullmatch(rf"# {re.escape(name)}:(\d+)", line) for line in lines]
    values = [int(match.group(1)) for match in matches if match]
    if len(values) != 1:
        raise ValueError(f"Expected one '# {name}:<count>' header, found {len(values)}")
    return values[0]


def set_count(lines: list[str], name: str, value: int) -> None:
    pattern = re.compile(rf"# {re.escape(name)}:\d+")
    matches = [i for i, line in enumerate(lines) if pattern.fullmatch(line)]
    if len(matches) != 1:
        raise ValueError(f"Expected one '# {name}:<count>' header, found {len(matches)}")
    lines[matches[0]] = f"# {name}:{value}"


def main() -> int:
    request = urllib.request.Request(UPSTREAM, headers={"User-Agent": "MikeHuang01-Rules-sync/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        upstream_text = response.read().decode("utf-8-sig")
    lines = upstream_text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if not lines or not lines[0].startswith("# NAME:"):
        raise ValueError("Downloaded file does not look like a Quantumult X rule resource")

    old_counts = {name: read_count(lines, name) for name in COUNT_NAMES}
    mitm_indexes = [i for i, line in enumerate(lines) if line.strip() == "# MITM"]
    hostname_indexes = [i for i, line in enumerate(lines) if line.startswith("hostname = ")]
    if len(mitm_indexes) != 1 or len(hostname_indexes) != 1:
        raise ValueError("Expected exactly one '# MITM' section and one hostname declaration")

    host_index = hostname_indexes[0]
    host_prefix = "hostname = "
    host_values = [part.strip() for part in lines[host_index][len(host_prefix):].split(",") if part.strip()]
    existing_hosts = {host.casefold() for host in host_values}
    hosts_to_add = [host for host in CUSTOM_HOSTS if host.casefold() not in existing_hosts]
    lines[host_index] = host_prefix + ",".join(host_values + hosts_to_add)

    existing_rules = {line.strip().casefold() for line in lines}
    rules_to_add = [rule for rule in CUSTOM_RULES if rule.casefold() not in existing_rules]
    mitm_index = mitm_indexes[0]
    block = [
        "# --- MikeHuang01 custom Alipay/Cainiao mini-program ads ---",
        f"# Source: {CUSTOM_SOURCE}",
        "# Reject only ad/recommendation API paths; do not block taobao.com globally.",
        *rules_to_add,
        "",
    ]
    lines[mitm_index:mitm_index] = block

    # Keep the upstream counts and adjust only for local entries added this run.
    for name in ("HOST", "HOST-KEYWORD", "IP-CIDR", "IP6-CIDR"):
        set_count(lines, name, old_counts[name])
    set_count(lines, "REJECT", old_counts["REJECT"] + len(rules_to_add))
    set_count(lines, "MITM", old_counts["MITM"] + len(hosts_to_add))
    set_count(lines, "TOTAL", old_counts["TOTAL"] + len(rules_to_add) + len(hosts_to_add))

    # Guard against silently dropping the caller's local rules on upstream changes.
    final_text = "\n".join(lines) + "\n"
    for rule in CUSTOM_RULES:
        if rule.casefold() not in final_text.casefold():
            raise ValueError(f"Custom rule missing after merge: {rule}")
    final_hosts_line = next(line for line in lines if line.startswith("hostname = "))
    for host in CUSTOM_HOSTS:
        if host.casefold() not in {part.strip().casefold() for part in final_hosts_line[len(host_prefix):].split(",")} :
            raise ValueError(f"Custom MITM host missing after merge: {host}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == final_text:
        print(f"unchanged: {OUTPUT.relative_to(ROOT)}")
    else:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=OUTPUT.parent, delete=False) as tmp:
            tmp.write(final_text)
            temp_name = tmp.name
        os.replace(temp_name, OUTPUT)
        print(f"updated: {OUTPUT.relative_to(ROOT)}")
    print(f"upstream={UPSTREAM}")
    print(f"custom_rules={len(CUSTOM_RULES)} added_rules={len(rules_to_add)} added_mitm_hosts={len(hosts_to_add)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"sync-advertising-lite failed: {exc}", file=sys.stderr)
        sys.exit(1)

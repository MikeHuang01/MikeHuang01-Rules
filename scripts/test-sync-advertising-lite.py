#!/usr/bin/env python3
"""Offline regression for retaining targeted rules during upstream regeneration."""
from __future__ import annotations

import contextlib
import io
import runpy
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "QuantumultX" / "AdvertisingLite.conf"
module = runpy.run_path(str(ROOT / "scripts" / "sync-advertising-lite.py"), run_name="sync_test")
lines = CONF.read_text(encoding="utf-8").splitlines()
rules = module["CUSTOM_RULES"]
hosts = module["CUSTOM_HOSTS"]

# Reconstruct an upstream-like base by removing only the local generated block.
local_comments = (
    "# --- MikeHuang01 targeted app-ad response filters ---",
    "# Cainiao rules source:",
    "# The response script changes only recognized ad payload shapes on shared API paths.",
)
rule_set = {rule.casefold() for rule in rules}
base = [
    line for line in lines
    if line.strip().casefold() not in rule_set
    and not any(line.startswith(comment) for comment in local_comments)
]
for index, line in enumerate(base):
    if line.startswith("hostname = "):
        existing = [part.strip() for part in line[len("hostname = "):].split(",") if part.strip()]
        base[index] = "hostname = " + ",".join(
            host for host in existing if host.casefold() not in {item.casefold() for item in hosts}
        )
    elif line.startswith("# REJECT:"):
        base[index] = f"# REJECT:{int(line.split(':', 1)[1]) - len(rules)}"
    elif line.startswith("# MITM:"):
        base[index] = f"# MITM:{int(line.split(':', 1)[1]) - len(hosts)}"
    elif line.startswith("# TOTAL:"):
        base[index] = f"# TOTAL:{int(line.split(':', 1)[1]) - len(rules) - len(hosts)}"
base_text = "\n".join(base) + "\n"

with tempfile.TemporaryDirectory() as temp_dir:
    output = Path(temp_dir) / "AdvertisingLite.conf"
    module["main"].__globals__["ROOT"] = Path(temp_dir)
    module["main"].__globals__["OUTPUT"] = output
    stdout = io.StringIO()
    with patch.dict(module, {"fetch": lambda _url: base_text}):
        with contextlib.redirect_stdout(stdout):
            assert module["main"]() == 0
    regenerated = output.read_text(encoding="utf-8")
    assert all(rule in regenerated.splitlines() for rule in rules)
    host_line = next(line for line in regenerated.splitlines() if line.startswith("hostname = "))
    generated_hosts = {host.strip().casefold() for host in host_line[len("hostname = "):].split(",")}
    assert all(host.casefold() in generated_hosts for host in hosts)
    assert "added_rules=7 added_mitm_hosts=6" in stdout.getvalue()

print("PASS: sync regeneration restores 7 local rules and 6 MITM hosts")

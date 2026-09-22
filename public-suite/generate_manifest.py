#!/usr/bin/env python3
"""Write a deterministic SHA-256 manifest for public-suite files."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "SHA256SUMS"

rows = []
for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
    if path == OUT or "__pycache__" in path.parts or path.suffix == ".pyc":
        continue
    rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT)}")
OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} hashes to {OUT.name}")

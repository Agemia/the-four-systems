#!/usr/bin/env python3
"""Print the next queued content-queue item as JSON, or exit 2 if nothing queued.

The Content Writer (System 2) calls this at the start of an auto-pilot run to
get the brief. Items are selected by Business Value Score (BVS) desc, then by
volume desc as a tiebreaker. Items with `bvs <= 1` or `zero_click_trap: true`
are skipped — the writer would refuse them anyway. Items with no `bvs` field
(legacy entries) are treated as bvs=5 so they don't starve.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

QUEUE = Path(__file__).resolve().parent.parent / "state" / "content-queue.json"


def _sort_key(item: dict) -> tuple:
    bvs = item.get("bvs")
    if bvs is None:
        bvs = 5  # legacy default
    volume = item.get("volume") or 0
    return (-bvs, -volume)


def main() -> int:
    if not QUEUE.exists():
        print("ERROR: content-queue.json not found", file=sys.stderr)
        return 1
    data = json.loads(QUEUE.read_text())
    queued = [
        i for i in data.get("items", [])
        if i.get("status") == "queued"
        and not i.get("zero_click_trap")
        and (i.get("bvs") is None or i["bvs"] > 1)
    ]
    if not queued:
        print("NO_QUEUED_ITEMS", file=sys.stderr)
        return 2
    queued.sort(key=_sort_key)
    json.dump(queued[0], sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

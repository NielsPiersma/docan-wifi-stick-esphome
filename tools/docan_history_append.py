#!/usr/bin/env python3
"""Append one raw Docan BMS history record to a text file.

Called by the Home Assistant automation "Docan - BMS history to file" for
every state of the text sensor "BMS history record" (format
"<n>;<ADR>;<INFO hex>").

Every read session gets its own file: record 1 starts a new file
  /config/docan/history/docan_history_pack_<pack>_<YYYY-MM-DD_HHMMSS>.txt
and the following records of that session are appended to it. So two reads
on the same day (for example an automatic read after a protection event)
never mix or duplicate records.

Usage: docan_history_append.py <pack> <record>
"""
import datetime
import os
import re
import sys

BASE = "/config/docan/history"


def main() -> int:
    if len(sys.argv) != 3:
        return 1
    pack, record = sys.argv[1].strip(), sys.argv[2].strip()
    if not re.fullmatch(r"[1-4]", pack):
        return 1
    if not re.fullmatch(r"\d+;[0-9A-F]{2};[0-9A-F]+", record):
        return 1
    os.makedirs(BASE, exist_ok=True)
    pointer = os.path.join(BASE, f".current_pack_{pack}")
    path = ""
    if record.startswith("1;"):
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = os.path.join(BASE, f"docan_history_pack_{pack}_{stamp}.txt")
        with open(pointer, "w", encoding="ascii") as handle:
            handle.write(path)
    elif os.path.exists(pointer):
        with open(pointer, encoding="ascii") as handle:
            path = handle.read().strip()
    if not path or not path.startswith(BASE + "/"):
        day = datetime.date.today().isoformat()
        path = os.path.join(BASE, f"docan_history_pack_{pack}_{day}.txt")
    with open(path, "a", encoding="ascii") as handle:
        handle.write(record + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

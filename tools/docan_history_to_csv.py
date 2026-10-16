#!/usr/bin/env python3
"""Convert raw Docan BMS history records into the CSV layout of DR BMS Monitor.

The vendor tool (BMS_Monitor / DR BMS Monitor V1.0.2.9, History > Standard
Data > Export data) writes one row per history record. This script decodes
the raw DR-1363 service 0x4B answers that the ESPHome stick publishes
("<n>;<ADR>;<INFO hex>", one per line, see docan_history_append.py) with the
same field offsets, scaling and number formats as the vendor tool, and writes
the same columns. Encoding GB2312 and CRLF line ends, like the vendor tool.

Usage:
  docan_history_to_csv.py <input.txt> [<input.txt> ...]
Writes HistoryStandardData_<input name>.csv next to each input file.
"""
import os
import sys

MAX_CELL = 24   # the vendor tool always exports 24 cell columns
MAX_TEMP = 8    # and 8 temperature columns

EVENTS = {
    1: 'Cell OV PROT',
    2: 'Cell UNV PROT',
    3: 'TOT OV PROT',
    4: 'TOT UNV PROT',
    5: 'CHG OC 1 PROT',
    6: 'CHG OC 2 PROT',
    7: 'DISCH OC 1 PROT',
    8: 'DISCH OC 2 PROT',
    9: 'Short-circuit PROT',
    10: 'CHG OT PROT',
    11: 'CHG UNT PROT',
    12: 'DISCH OT PROT',
    13: 'DISCH UNT PROT',
    14: 'Enter CHG',
    15: 'Enter DISCH',
    16: 'Time recording',
    17: 'DISCH OC PROT Lock',
    18: 'Short-circuit PROT Lock',
    19: 'Reverse connect PROT',
    20: 'Enter sleep',
    21: 'Enter the current limit',
    22: 'CHG MOS fault',
    23: 'DISCH MOS fault',
    24: 'System run',
    25: 'Charge into lock',
    26: 'Battery lock',
    27: 'Volts diff PROT',
    28: 'AFE fault',
    29: 'NTC failure',
    30: 'Full charge PROT',
    31: 'Break PROT',
    32: 'MOS OT',
    33: 'ENV OT',
    34: 'ENV UNT',
    35: 'Release device action',
    36: 'Anti theft lock',
    37: 'DISCH prohibited',
    38: 'CHG prohibited',
    39: 'Factory clearing logs',
    40: 'User clearing logs',
    41: 'Version change',
    42: 'Parameter changes',
    43: 'Enter Tooling mode',
    44: 'Depth UNV fault',
    45: 'Abnormal cell',
    46: 'Pack volt fault',
    47: 'Aeros active',
    48: 'Aeros over temp active ',
    49: 'Fuse broken',
    128: 'Cell OV PROT release',
    129: 'Cell UNV PROT release',
    130: 'TOT OV PROT release',
    131: 'TOT UNV PROT release',
    132: 'CHG OC 1 PROT release',
    133: 'CHG OC 2 PROT release',
    134: 'DISCH OC 1 PROT release',
    135: 'DISCH OC 2 PROT release',
    136: 'Short-circuit PROT release',
    137: 'CHG OT release',
    138: 'CHG UNT release',
    139: 'DISCH OT release',
    140: 'DISCH UNT release',
    141: 'Exit CHG',
    142: 'Exit DISCH',
    144: 'CHG OC Exit lock',
    145: 'Short-circuit PROT Exit lock',
    146: 'Back-Up PROT release',
    148: 'Exit Limit current',
    149: 'Reserve',
    150: 'Reserve',
    151: 'Reserve',
    152: 'CHG Exit lock',
    153: 'Battery Exit lock',
    154: 'Volts diff PROT release',
    156: 'NTC break release',
    157: 'Exit full PROT',
    158: 'Break PROT release',
    159: 'MOS OT release',
    160: 'ENV OT release',
    161: 'ENV UNT release',
    162: 'AFE fault release',
    163: 'Release reset',
    164: 'Anti theft release',
    165: 'DISCH prohibited release',
    166: 'CHG prohibited release',
    167: 'Exit Tooling mode',
    168: 'Depth UNV release',
    169: 'Exit Abnormal cell',
    170: 'Exit pack volt fault',
    171: 'Exit aeros',
    172: 'Exit aeros over temp',
    65535: 'Normal record',
}

ALARM_BITS = {
    0: 'Cell OV alarm',
    1: 'Cell UNV alarm',
    2: 'Cell abnormal',
    3: 'Voltage difference alarm',
    4: 'Total voltage is too high alarm',
    5: 'Total voltage is too low alarm',
    6: 'ENV H TEMP alarm',
    7: 'ENV L TEMP alarm',
    8: 'MOS L TEMP alarm',
    9: 'MOS H TEMP alarm',
    10: 'Battery CHG is hot alarm',
    11: 'Battery CHG is cold alarm',
    12: 'Battery DISCH is hot alarm',
    13: 'Battery DISCH is cold alarm',
    14: 'TEMP Diff is too large alarm',
    15: 'CHG MOS fault',
    16: 'DISCH MOS fault',
    17: 'CHG OC1 alarm',
    18: 'DISCH 0C1 alarm',
    19: 'Charging cabinet communication alarm',
    20: 'GPRS communication alert alarm',
    21: 'Fire alarm',
}

PROTECT_BITS = {
    0: 'Cell OV PROT',
    1: 'Cell UNV PROT',
    2: 'TOT OV PROT',
    3: 'TOT UNV PROT',
    4: 'CHG OC 1 PROT',
    5: 'CHG OC 2 PROT',
    6: 'DISCH OC 1 PROT',
    7: 'DISCH OC 2 PROT',
    8: 'Short-circuit PROT',
    9: 'CHG OT PROT',
    10: 'CHG UNT PROT',
    11: 'DISCH OT PROT',
    12: 'DISCH UNT PROT',
    13: 'Reverse connect PROT',
    14: 'CHG MOS fault',
    15: 'DISCH MOS fault',
    16: 'Battery lock',
    17: 'Volts diff PROT',
    18: 'AFE fault',
    19: 'Full charge PROT',
    20: 'Break PROT',
    21: 'Blown fuse',
    22: 'SOC LOW PROT',
    23: 'Reserve',
    24: 'Current limiting is frequently protected',
    25: 'Sampling failure',
    26: 'NTC fault',
    27: 'The system is faulty',
}

HEADER = (
    ["No", "Pack", "Time", "Local time", "EventRecord", "Total voltage(V)",
     "Total current(A)", "Number of charges", "Number of discharges", "SOC(%)",
     "SOH(%)", "Full capacity(Ah)", "Env TEMP(\u2103)", "MOS TEMP(\u2103)",
     "Alert state", "PROT state", "Cell Num", "V difference(mV)"]
    + [f"Cell {i}" for i in range(1, MAX_CELL + 1)]
    + ["Temp quantity"]
    + [f"TEMP {i}" for i in range(1, MAX_TEMP + 1)]
)


def u16(p, i):
    return (p[i] << 8) | p[i + 1]


def s16(p, i):
    v = u16(p, i)
    return v - 0x10000 if v & 0x8000 else v


def bits(value, names):
    # Same as the vendor tool: every set bit, each followed by ';'.
    out = ""
    for i in range(32):
        if value >> i & 1:
            out += names.get(i, f"bit {i}") + ";"
    return out


def decode(record):
    """Decode one '<n>;<ADR>;<hex>' record into a dict (INFO offsets)."""
    n, adr, hexdata = record.strip().split(";")
    p = bytes.fromhex(hexdata)
    # p[0] = 00 more records / 01 last record, p[1] unused,
    # p[2..7] = YY MM DD hh mm ss, fields from b = 8 (vendor tool: data[14]).
    b = 8
    time = (f"{2000 + p[2]:04d}-{p[3]:02d}-{p[4]:02d} "
            f"{p[5]:02d}:{p[6]:02d}:{p[7]:02d}")
    cells_n = p[b + 35]
    cells = [u16(p, b + 36 + 2 * i) * 0.001 for i in range(cells_n)]
    f = b + 36 + 2 * cells_n
    temps_n = p[f]
    temps = [s16(p, f + 1 + 2 * j) * 0.1 for j in range(temps_n)]
    e = f + 1 + 2 * temps_n
    event = u16(p, e) if e + 1 < len(p) else 0xFFFF
    return {
        "n": int(n),
        "pack": int(adr, 16),
        "time": time,
        "event": EVENTS.get(event, EVENTS[65535]),
        "voltage": u16(p, b) * 0.1,
        "current": s16(p, b + 2) * 0.1,
        "charges": u16(p, b + 4),
        "discharges": u16(p, b + 6),
        "soh": u16(p, b + 16) * 0.1,
        "soc": u16(p, b + 18) * 0.1,
        "full_capacity": float(u16(p, b + 21)),
        "env_temp": s16(p, b + 23) * 0.1,
        "mos_temp": s16(p, b + 25) * 0.1,
        "alarm": bits((p[b + 27] << 24) | (p[b + 28] << 16) | (p[b + 29] << 8) | p[b + 30], ALARM_BITS),
        "protect": bits((p[b + 31] << 24) | (p[b + 32] << 16) | (p[b + 33] << 8) | p[b + 34], PROTECT_BITS),
        "cells": cells,
        "temps": temps,
    }


def row(index, r):
    cells = r["cells"]
    diff = (max(cells) - min(cells)) * 1000 if cells else 0
    out = [str(index), str(r["pack"]), r["time"], "", r["event"],
           f"{r['voltage']:.2f}", f"{r['current']:.2f}", str(r["charges"]),
           str(r["discharges"]), f"{r['soc']:.2f}", f"{r['soh']:.2f}",
           f"{r['full_capacity']:.0f}", f"{r['env_temp']:.1f}", f"{r['mos_temp']:.1f}",
           r["alarm"], r["protect"], str(len(cells)), f"{diff:.0f}"]
    out += [f"{cells[i]:.3f}" if i < len(cells) else "" for i in range(MAX_CELL)]
    out += [str(len(r["temps"]))]
    out += [f"{r['temps'][j]:.1f}" if j < len(r["temps"]) else "" for j in range(MAX_TEMP)]
    return ",".join(out)


def convert(path):
    records = []
    with open(path, encoding="ascii") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(decode(line))
            except (ValueError, IndexError) as error:
                print(f"{path}: skipped line ({error}): {line[:60]}", file=sys.stderr)
    name = os.path.splitext(os.path.basename(path))[0]
    target = os.path.join(os.path.dirname(path) or ".", f"HistoryStandardData_{name}.csv")
    with open(target, "w", encoding="gb2312", newline="") as handle:
        handle.write(",".join(HEADER) + "\r\n")
        for i, r in enumerate(records, 1):
            handle.write(row(i, r) + "\r\n")
    print(f"{target}: {len(records)} records")
    return target


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for argument in sys.argv[1:]:
        convert(argument)

"""Read original attachments without depending on any previous result."""
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import hashlib
import json
import math
import openpyxl

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    lon: float
    lat: float
    ground_m: float

    @property
    def work_m(self):
        return self.ground_m + (0 if self.id == 'O01' else 30)


@dataclass(frozen=True)
class Aircraft:
    id: str
    name: str
    empty_kg: float
    rated_kg: float
    volume_m3: float
    cruise_mps: float
    empty_range_m: float
    full_range_m: float
    battery_kwh: float
    reserve_pct: float
    prep_s: float
    load_s: float
    handover_s: float
    handover_box_s: float
    up_mps: float
    down_mps: float
    up_eff: float
    down_eff: float


@dataclass(frozen=True)
class Box:
    id: str
    area: str
    kind: str
    mass_kg: float
    volume_m3: float


def rows(path, sheet=0):
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = book.worksheets[sheet] if isinstance(sheet, int) else book[sheet]
    data = list(ws.values)
    book.close()
    return data


def load_inputs(raw=None):
    raw = Path(raw or ROOT / 'data/raw')
    ns = rows(raw / '调度中心与服务区.xlsx')
    nodes = {r[0]: Node(*r[:5]) for r in ns
             if isinstance(r[0], str) and (r[0] == 'O01' or r[0].startswith('S0'))}
    ar = rows(raw / '运输无人机数据.xlsx')
    head = next(i for i,r in enumerate(ar) if r[0] == '机型编号' and r[2] == '含电池空载总质量（kg）')
    aircraft = {}
    for r in ar[head+1:]:
        if r[0] is None:
            break
        if r[0] in aircraft:
            raise ValueError('Duplicate type in aircraft parameter section')
        aircraft[r[0]] = Aircraft(*r[:18])
    br = rows(raw / '物资需求与配送时限.xlsx', '逐箱货箱清单')
    boxes = [Box(*r[:5]) for r in br[1:] if r[0] is not None]
    if len(nodes) != 16 or len(aircraft) != 3 or len(boxes) != 80:
        raise ValueError('Unexpected raw instance dimensions')
    if len({b.id for b in boxes}) != len(boxes):
        raise ValueError('Duplicate original box id')
    actual = Counter((b.area, b.kind, b.mass_kg, b.volume_m3) for b in boxes)
    demand = {(r[0], r[1], r[4], r[5]): r[2]
              for r in rows(raw / '物资需求与配送时限.xlsx')[1:] if r[0] is not None}
    if actual != demand:
        raise ValueError('Box list disagrees with demand summary')
    if any(b.area not in nodes or b.mass_kg <= 0 or b.volume_m3 <= 0 for b in boxes):
        raise ValueError('Invalid box record')
    for a in aircraft.values():
        if not (0 < a.full_range_m <= a.empty_range_m and 0 < a.up_eff <= 1
                and a.down_eff == 0 and 0 <= a.reserve_pct < 100):
            raise ValueError('Unsupported or invalid aircraft parameters')
    return nodes, aircraft, boxes


def provenance(raw=None):
    raw = Path(raw or ROOT / 'data/raw')
    return [{'file': p.name, 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(raw.iterdir()) if p.is_file()]


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path, records, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = list(records)
    fields = fields or list(records[0])
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, tuple, dict)) else v)
                             for k, v in record.items()})

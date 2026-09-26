#!/usr/bin/env python3
"""Materialize only the SHA-locked Q2 inputs needed by these experiments."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, zipfile
EXPECTED = '0804f989699dc506b3111dacc7408d9acdeb6e1115e7f32ec36934116de6ce58'
FILES = {'flights.json','stops.json','decisions.json','phases.json','deliveries.json','metrics.json','legs.json','battery_cycles.json'}

def bootstrap(archive: Path, destination: Path) -> int:
    archive = archive.resolve(); destination = destination.resolve()
    with archive.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    if digest != EXPECTED:
        raise ValueError('Wrong Q2 evidence archive SHA-256; no files written')
    selected = []
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = PurePosixPath(info.filename)
            if name.is_absolute() or '..' in name.parts:
                raise ValueError('Unsafe archive path')
            rel = None
            for prefix, target in [
                ('q2_evidence_v7/upstream/primal/code/', 'q2_runtime/code/'),
                ('q2_evidence_v7/upstream/primal/inputs/', 'q2_runtime/inputs/')]:
                if info.filename.startswith(prefix):
                    suffix = info.filename[len(prefix):]
                    if '__pycache__' not in PurePosixPath(suffix).parts and not suffix.endswith('.pyc'):
                        rel = target + suffix
            prefix = 'q2_evidence_v7/results/incumbent_replay/'
            if info.filename.startswith(prefix) and info.filename[len(prefix):] in FILES:
                rel = 'inputs/q2/' + info.filename[len(prefix):]
            if rel is not None:
                dest = (destination / rel).resolve()
                if not dest.is_relative_to(destination):
                    raise ValueError('Destination escapes experiment directory')
                data = z.read(info)
                if dest.exists() and dest.read_bytes() != data:
                    raise ValueError('Existing input differs; use an empty destination: ' + str(dest))
                selected.append((dest, data))
    if not FILES.issubset({p.name for p, _ in selected if p.parent == destination/'inputs/q2'}):
        raise ValueError('Formal incumbent input files incomplete')
    for dest, data in selected:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    return len(selected)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--destination', type=Path, default=Path(__file__).resolve().parent)
    a = p.parse_args()
    print('INPUTS_VERIFIED', bootstrap(a.archive, a.destination))

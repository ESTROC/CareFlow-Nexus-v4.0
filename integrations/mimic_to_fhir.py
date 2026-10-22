#!/usr/bin/env python3
"""Transform a small, LOCAL MIMIC-IV demo hospital subset into FHIR R4-shaped resources.

Only official open demo CSVs; no cross-dataset joins, no live server writes, no
clinical decision support. Source identifiers remain locally linkable, so
exports must not be put in a public repository or shared externally.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path


def read_rows(folder: Path, stem: str):
    gz = folder / f'{stem}.csv.gz'
    plain = folder / f'{stem}.csv'
    if gz.exists():
        with gzip.open(gz, 'rt', newline='', encoding='utf8') as f:
            yield from csv.DictReader(f)
    elif plain.exists():
        with plain.open(newline='', encoding='utf8') as f:
            yield from csv.DictReader(f)
    else:
        raise FileNotFoundError(f'Missing {stem}.csv(.gz) in {folder}')


def build_bundle(folder: Path, limit: int = 30):
    if limit < 1 or limit > 100:
        raise ValueError('limit must be between 1 and 100 for the demo dataset')
    patients = {}
    for row in read_rows(folder, 'patients'):
        sid = row['subject_id']
        gender = {'M': 'male', 'F': 'female'}.get(row.get('gender'), 'unknown')
        patients[sid] = {'resourceType': 'Patient', 'id': f'mimic-demo-{sid}', 'gender': gender,
                         'meta': {'tag': [{'system': 'https://careflow.example/provenance', 'code': 'MIMIC-IV-DEMO-2.2'}]}}
    entries = []
    selected = set()
    for row in read_rows(folder, 'admissions'):
        sid = row.get('subject_id', '')
        if sid not in patients:
            continue
        if len(selected) >= limit and sid not in selected:
            continue
        if sid not in selected:
            selected.add(sid)
            entries.append({'resource': patients[sid]})
        hadm_id = row.get('hadm_id')
        if not hadm_id:
            continue
        encounter = {'resourceType': 'Encounter', 'id': f'mimic-demo-{hadm_id}',
                     'status': 'finished',
                     'class': {'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode', 'code': 'IMP'},
                     'subject': {'reference': f'Patient/mimic-demo-{sid}'},
                     'period': {'start': row.get('admittime'), 'end': row.get('dischtime')},
                     'meta': {'tag': [{'system': 'https://careflow.example/provenance', 'code': 'MIMIC-IV-DEMO-2.2'}]}}
        entries.append({'resource': encounter})
    if not selected:
        raise ValueError('No linked patients/admissions found')
    return {'resourceType': 'Bundle', 'type': 'collection', 'entry': entries}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True, help='Local MIMIC-IV demo 2.2 hosp directory')
    p.add_argument('--out', type=Path, required=True, help='Output under gitignored research/data')
    p.add_argument('--limit', type=int, default=30)
    args = p.parse_args()
    if 'research/data' not in args.out.as_posix() and not args.out.as_posix().startswith('/tmp/'):
        raise SystemExit('For safety, write only under research/data/ or /tmp/. Never commit this bundle.')
    bundle = build_bundle(args.directory, args.limit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2), encoding='utf8')
    print(f'Created local FHIR-shaped bundle of {len(bundle["entry"])} resources at {args.out}. Do not commit it.')


if __name__ == '__main__':
    main()

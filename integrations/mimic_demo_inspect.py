#!/usr/bin/env python3
"""Read open MIMIC-IV demo CSV.gz files LOCALLY; never merge with synthetic cases.

Example: python integrations/mimic_demo_inspect.py --directory research/data/mimic-iv-demo/2.2/hosp
Only prints aggregate row counts and schema metadata; no patient-level export.
"""
import argparse
import csv
import gzip
import json
from pathlib import Path


def summarize(directory: Path):
    names=['patients.csv.gz','admissions.csv.gz','labevents.csv.gz','prescriptions.csv.gz']
    output={"dataset":"MIMIC-IV Clinical Database Demo 2.2",
            "source":"https://physionet.org/content/mimic-iv-demo/2.2/",
            "note":"De-identified source data; no cross-dataset patient joins.","tables":{}}
    for name in names:
        path=directory/name
        if not path.is_file():
            continue
        with gzip.open(path,'rt',newline='',encoding='utf8') as handle:
            reader=csv.DictReader(handle)
            count=sum(1 for _ in reader)
            output["tables"][name]={"rows":count,"columns":reader.fieldnames}
    if not output["tables"]:
        raise SystemExit(f'No known .csv.gz MIMIC tables in {directory}; use the official demo files')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(summarize(args.directory),indent=2))

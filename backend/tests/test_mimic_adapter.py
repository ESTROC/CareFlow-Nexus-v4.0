"""Tests with invented rows, not extracted patient data."""
import csv
import gzip
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'integrations'))
from mimic_to_fhir import build_bundle


def write_rows(path, data):
    with gzip.open(path, 'wt', newline='', encoding='utf8') as f:
        out=csv.DictWriter(f, fieldnames=list(data[0]))
        out.writeheader();out.writerows(data)


def test_fhir_export_does_not_join_unrelated_patients(tmp_path):
    write_rows(tmp_path/'patients.csv.gz', [{'subject_id':'42','gender':'F'}])
    write_rows(tmp_path/'admissions.csv.gz', [
        {'subject_id':'42','hadm_id':'99','admittime':'2150-01-01 10:00:00','dischtime':'2150-01-03 10:00:00'},
        {'subject_id':'999','hadm_id':'9999','admittime':'2150-01-01','dischtime':'2150-01-02'}])
    result=build_bundle(tmp_path)
    assert result['resourceType']=='Bundle'
    resources=[i['resource'] for i in result['entry']]
    assert [r['resourceType'] for r in resources]==['Patient','Encounter']
    assert resources[1]['subject']['reference']=='Patient/mimic-demo-42'
    assert 'mimic-demo-9999' not in str(result)
    assert resources[1]['meta']['tag'][0]['code']=='MIMIC-IV-DEMO-2.2'

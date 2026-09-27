"""Create minimal compressed analysis tables from the supplied Synthea CSVs."""
import argparse,csv,gzip,hashlib,json
from pathlib import Path
COLUMNS={
 'patients':['Id','BIRTHDATE','DEATHDATE','GENDER','RACE'],
 'conditions':['PATIENT','DESCRIPTION','START'],
 'medications':['PATIENT','DESCRIPTION','START'],
 'encounters':['PATIENT','ENCOUNTERCLASS','START'],
}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('source',type=Path); args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]; out=root/'data'/'raw';out.mkdir(exist_ok=True)
    manifest={'reference_date':'2024-10-04','reference_date_basis':'Latest observed encounter START date in supplied export; not a verified simulator end date.',
       'source':'User-supplied Delaware Synthea CSV export','generator_version':'Unknown','seed':'Unknown','tables':{}}
    for name,columns in COLUMNS.items():
        src=args.source/(name+'.csv'); dst=out/(name+'.csv.gz'); n=0
        with src.open(newline='') as f, gzip.open(dst,'wt',newline='',encoding='utf-8') as g:
            reader=csv.DictReader(f);writer=csv.DictWriter(g,fieldnames=columns);writer.writeheader()
            for row in reader:writer.writerow({c:row[c] for c in columns});n+=1
        manifest['tables'][name]={'rows':n,'columns':columns,'source_sha256':digest(src),'analysis_sha256':digest(dst)}
    (root/'data'/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()

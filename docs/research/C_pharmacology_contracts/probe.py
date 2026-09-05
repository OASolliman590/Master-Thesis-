"""Bounded public contract probes; no credentials or expression matrices."""
import hashlib
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).parent
URLS = {
    "geo70138_listing.html": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/",
    "lincs2020_README.txt": "https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/README.txt",
    "lincs2020_cellinfo.txt": "https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/cellinfo_beta.txt",
    "lincs2020_geneinfo.txt": "https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/geneinfo_beta.txt",
    "lincs2020_compoundinfo.txt": "https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/compoundinfo_beta.txt",
    "prism19q4_manifest.json": "https://api.figshare.com/v2/articles/9393293",
    "chembl_status.json": "https://www.ebi.ac.uk/chembl/api/data/status.json",
    "chembl_three_molecules.json": "https://www.ebi.ac.uk/chembl/api/data/molecule.json?pref_name__in=DECITABINE,ENTINOSTAT,TAZEMETOSTAT&limit=20",
    "gdsc_directory.html": "https://ftp.sanger.ac.uk/pub/project/cancerrxgene/releases/current_release/",
}
total = 0
log = []
for name, url in URLS.items():
    try:
        with urllib.request.urlopen(url, timeout=40) as response:
            raw = response.read(min(20_000_000, 50_000_000-total)+1)
            total += len(raw)
            if len(raw)>20_000_000 or total>50_000_000:
                raise ValueError("Public download size cap exceeded")
            (ROOT/name).write_bytes(raw)
            log.append(dict(file=name,url=url,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),status="success"))
    except Exception as error:
        log.append(dict(file=name,url=url,status="failed",error=str(error)))
(ROOT/"access_manifest.json").write_text(json.dumps(log,indent=2))
print(json.dumps(log,indent=2))

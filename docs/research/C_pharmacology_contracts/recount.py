"""Recount cached metadata only; does not run compound scoring."""
import collections
import csv
import gzip
import json
from pathlib import Path

root = Path(__file__).parent
def tsv(name):
    return list(csv.DictReader((root/name).open(), delimiter="\t"))

genes = tsv("lincs2020_geneinfo.txt")
compounds = tsv("lincs2020_compoundinfo.txt")
cells = tsv("lincs2020_cellinfo.txt")
molecules = json.loads((root/"chembl_three_molecules.json").read_text())["molecules"]
with gzip.open(root/"GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz", "rt") as stream:
    signatures = list(csv.DictReader(stream, delimiter="\t"))
summary = {
    "scope": "LINCS2020 annotations plus GSE70138 2017-03-06 signatures; no matrix QC",
    "gene_feature_counts": dict(collections.Counter(x["feature_space"] for x in genes)),
    "sentinel_features": [{"gene":x["gene_symbol"],"feature_space":x["feature_space"]} for x in genes if x["gene_symbol"] in {"CXCL9","CXCL10","HLA-A","HLA-B","HLA-C","B2M","TAP1","TAP2","PSMB8","PSMB9"}],
    "prostate_lookup_rows": [x for x in cells if x["cell_lineage"]=="prostate"],
    "phase2_signature_count": len(signatures),
    "phase2_prostate_chemical_counts": dict(collections.Counter(x["cell_id"] for x in signatures if x["pert_type"]=="trt_cp" and x["cell_id"] in {"PC3","LNCAP","DU145","VCAP","22RV1"})),
    "three_drugs": [],
}
for molecule in molecules:
    key=molecule["molecule_structures"]["standard_inchi_key"]
    matches=[x for x in compounds if x["inchi_key"]==key]
    ids={x["pert_id"] for x in matches}
    hits=[x for x in signatures if x["pert_id"] in ids and x["pert_type"]=="trt_cp"]
    prostate=[x for x in hits if x["cell_id"] in {"PC3","LNCAP","DU145","VCAP","22RV1"}]
    summary["three_drugs"].append({"name":molecule["pref_name"],"chembl_id":molecule["molecule_chembl_id"],"inchi_key":key,"lincs_compound_rows":matches,"phase2_all_signatures":len(hits),"phase2_prostate_signatures":len(prostate),"conditions":[{"cell":k[0],"dose":k[1],"time":k[2],"signatures":v} for k,v in collections.Counter((x["cell_id"],x["pert_idose"],x["pert_itime"]) for x in prostate).items()],"distil_id_count_distribution":dict(collections.Counter(len(x["distil_id"].split("|")) for x in prostate))})
summary["prism"]={}
for name in ("primary-screen-cell-line-info.csv","secondary-screen-cell-line-info.csv"):
    rows=list(csv.DictReader((root/name).open()))
    summary["prism"][name]={"lookup_rows":len(rows),"prostate_rows":[x for x in rows if x["primary_tissue"]=="prostate"]}
rows=list(csv.DictReader((root/"primary-screen-replicate-collapsed-treatment-info.csv").open()))
summary["prism"]["primary_treatment_rows"]=len(rows)
summary["prism"]["three_drugs"]=[x for x in rows if x["name"].lower() in {"decitabine","entinostat","tazemetostat"}]
(root/"verified_coverage_summary.json").write_text(json.dumps(summary,indent=2))
print("Wrote metadata-only verified_coverage_summary.json")

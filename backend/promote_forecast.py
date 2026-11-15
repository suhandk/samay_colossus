"""Explicit research deployment only; never grants validated status."""
import argparse,json,hashlib
from pathlib import Path
from .db import Session
from .models import Crop,Market

def main():
    parser=argparse.ArgumentParser();parser.add_argument('version');args=parser.parse_args()
    if '/' in args.version or '\\' in args.version or args.version.startswith('.'):raise ValueError('Invalid version')
    root=Path(__file__).resolve().parents[1];folder=root/'models/evaluated'/args.version;report=json.loads((folder/'evaluation.json').read_text())
    if report['status']!='evaluated_research_only' or report['holdout']['n']<15:raise ValueError('Evaluation incomplete')
    model=(folder/'model.pkl').read_bytes()
    if hashlib.sha256(model).hexdigest()!=report['model_sha256']:raise ValueError('Artifact changed since evaluation')
    with Session() as db:
        crop=db.get(Crop,report['scope']['crop']);market=db.get(Market,report['scope']['market'])
        metadata={**report,'version':args.version,'candidate':{'last':'naive','mean14':'mean_14'}.get(report['candidate'],report['candidate']),'commodity':crop.names['en'],'market':market.names['en'],'variety':report['scope']['variety'],'grade':report['scope']['grade'],'trained_before':report['trained_at'],'training_window':report['partitions']['train']['origins'],'empirical_calibration':{'radii':{'.9':report['calibration']['radius']} if report['calibration']['radius'] is not None else {}},'selection_report_sha256':hashlib.sha256((folder/'evaluation.json').read_bytes()).hexdigest()}
    target=root/'models/promoted'/args.version;target.mkdir(parents=True,exist_ok=False)
    raw=json.dumps(metadata,indent=2).encode();(target/'metadata.json').write_bytes(raw);(target/'model.pkl').write_bytes(model)
    (root/'models/evidence'/metadata['selection_report_sha256']).write_bytes((folder/'evaluation.json').read_bytes())
    path=root/'config/model-registry.json';registry=json.loads(path.read_text())
    entry={k:metadata[k] for k in ('version','commodity','market','variety','grade','horizon','candidate','trained_before','model_sha256')}
    entry.update(directory=target.relative_to(root).as_posix(),metadata_sha256=hashlib.sha256(raw).hexdigest(),status='evaluated_research_only')
    scope=('commodity','market','variety','grade','horizon');registry=[e for e in registry if tuple(e[k] for k in scope)!=tuple(entry[k] for k in scope)];registry.append(entry)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(registry,indent=2));temporary.replace(path)
    print('Explicitly deployed research version',args.version)
if __name__=='__main__':main()

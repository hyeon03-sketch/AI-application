"""EXPLORATORY (2026-10-06 night): annotator thresholds on each error's key kinematic feature, severity ordering,
and temporal-segment coverage. Groups 1A/2A only (no Group 3, pre-registration untouched). See RESEARCH_IDEAS.md."""
import csv, json, numpy as np, sys, pathlib
from sklearn.linear_model import LogisticRegression
sys.path.insert(0,'src'); from index import read_anvil
lab={r['rec_key']:r for r in csv.DictReader(open('data/labels.csv',encoding='utf-8'))}
idx={r['rec_key']:r for r in csv.DictReader(open('data/master_index.csv',encoding='utf-8'))}
f=np.load('data/features_T100.npz'); keys=list(f['keys']); names=[d['name'] for d in json.load(open('data/feature_names.json'))['Rerr']]
E=f['Rerr'].astype(float)
col=lambda n: E[:,:,names.index(n)]
F={'RTK':(('E2',),np.ptp(col('trunk_rotation'),axis=1)),
   'ELK':(('E2',),np.ptp(col('spine_tilt_frontal'),axis=1)),
   'CTK':(('E1','E3'),(col('shoulder_elev_L').max(1)+col('shoulder_elev_R').max(1))/2)}
def thr(x,y):
    if len(set(y))<2: return np.nan
    z=(x-x.mean())/x.std(); m=LogisticRegression(C=1e6,max_iter=5000).fit(z.reshape(-1,1),y)
    return x.mean()-m.intercept_[0]/m.coef_[0][0]*x.std()
rng=np.random.default_rng(0)
for ex,(errs,v) in F.items():
    sel=[i for i,k in enumerate(keys) if lab[k]['exercise']==ex and lab[k]['label_A'] in ('C',)+errs and lab[k]['label_B'] in ('C',)+errs]
    x=v[sel]; ya=np.array([lab[keys[i]]['label_A']!='C' for i in sel]); yb=np.array([lab[keys[i]]['label_B']!='C' for i in sel])
    g=np.array([lab[keys[i]]['participant_key'] for i in sel]); ids=np.unique(g); mem=[np.flatnonzero(g==p) for p in ids]
    obs=thr(x,yb)-thr(x,ya); bs=[]
    for _ in range(2000):
        pick=np.concatenate([mem[j] for j in rng.integers(0,len(ids),len(ids))])
        d=thr(x[pick],yb[pick])-thr(x[pick],ya[pick])
        if np.isfinite(d) and abs(d)<200: bs.append(d)
    lo,hi=np.percentile(bs,[2.5,97.5])
    print(f"{ex}: threshold B - A = {obs:+.1f} deg, participant-bootstrap 95% CI [{lo:+.1f}, {hi:+.1f}] (n={len(sel)}, {len(ids)} people, valid resamples {len(bs)})")
    for ann in 'AB':
        sm=[v[i] for i,k in enumerate(keys) if lab[k]['exercise']==ex and lab[k][f'label_{ann}'] in errs and lab[k][f'severity_{ann}']=='SmallError']
        lg=[v[i] for i,k in enumerate(keys) if lab[k]['exercise']==ex and lab[k][f'label_{ann}'] in errs and lab[k][f'severity_{ann}']=='LargeError']
        if sm and lg: print(f"   annotator {ann}: Small n={len(sm)} median {np.median(sm):.1f} | Large n={len(lg)} median {np.median(lg):.1f}")
fr=[]
for k,r in idx.items():
    if r['group'] in ('1A','2A') and r['ann_path_A'] and int(r['n_temporal_A'] or 0)>0:
        root=read_anvil(pathlib.Path(r['ann_path_A'])); tot=None; segs=[]
        for tr in root.iter('track'):
            for el in tr.findall('el'):
                s,e=float(el.get('start')),float(el.get('end'))
                if tr.get('name')=='Global evaluation': tot=e
                if tr.get('name')=='Temporal error': segs.append(e-s)
        if tot: fr.append(sum(segs)/tot)
fr=np.array(fr); print(f"\ntemporal error segments (annotator A): {len(fr)} recordings, median coverage {np.median(fr):.0%}, IQR {np.percentile(fr,25):.0%}-{np.percentile(fr,75):.0%}")

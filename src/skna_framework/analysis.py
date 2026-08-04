from __future__ import annotations
import numpy as np
import pandas as pd

RAW_ECG = ["ECG Gris 1 (d-s)", "ECG Pig 2 (c-c)", "ECG pig 3 (a-p)"]
FILT_ECG = ["ecg_filt__ECG Gris 1 (d-s)", "ecg_filt__ECG Pig 2 (c-c)", "ecg_filt__ECG pig 3 (a-p)"]
SKNA_CH = ["compact_skna_1", "compact_skna_2", "compact_skna_3"]
UAP_CANDS = ["Upper airway pressure", "UAP", "upper_airway_pressure"]


def first_existing(df, names):
    return next((n for n in names if n in df.columns), None)

def to_uv(x):
    """Convert stored processed SKNA envelope values from mV to µV.

    The supplied cohort *_signals_ecg_skna.csv files store compact_skna_* and
    skna_med in mV. The frozen threshold_summary.csv is in µV. Therefore the
    correct conversion is 1 mV = 1000 µV.
    """
    return np.asarray(x, float) * 1000.0

def event_row(events, pig_id):
    if events is None: return None
    key='file_id' if 'file_id' in events.columns else ('pig_id' if 'pig_id' in events.columns else None)
    if not key: return None
    r=events[pd.to_numeric(events[key], errors='coerce')==int(pig_id)]
    return None if r.empty else r.iloc[0]

def threshold_row(thresholds, pig_id):
    if thresholds is None or 'pig_id' not in thresholds.columns: return None
    r=thresholds[pd.to_numeric(thresholds['pig_id'],errors='coerce')==int(pig_id)]
    return None if r.empty else r.iloc[0]

def phase_masks(t,onset,offset,baseline_s=60,post_s=60):
    t=np.asarray(t,float)
    return {
        'Baseline': (t>=max(np.nanmin(t),onset-baseline_s)) & (t<onset),
        'INAP': (t>=onset)&(t<=offset),
        'Post-INAP': (t>offset)&(t<=offset+post_s),
    }

def phase_summary(t, skna_uv, threshold_uv, onset, offset, baseline_s=60, post_s=60):
    masks=phase_masks(t,onset,offset,baseline_s,post_s)
    rows=[]
    for name,m in masks.items():
        y=np.asarray(skna_uv,float)[m]
        rows.append({
            'phase':name,'n_samples':int(np.sum(np.isfinite(y))),
            'median_skna_uV':float(np.nanmedian(y)) if y.size else np.nan,
            'mean_skna_uV':float(np.nanmean(y)) if y.size else np.nan,
            'burst_occupancy_pct':float(100*np.nanmean(y>threshold_uv)) if y.size else np.nan,
        })
    out=pd.DataFrame(rows)
    base=float(out.loc[out.phase=='Baseline','median_skna_uV'].iloc[0])
    out['median_change_from_baseline_pct']=100*(out['median_skna_uV']-base)/base if base else np.nan
    return out

def sequential_replay(t, skna_uv, threshold_uv, window_s=30., hop_s=10., occupancy_threshold_pct=5., persistence=2):
    t=np.asarray(t,float); y=np.asarray(skna_uv,float)
    good=np.isfinite(t)&np.isfinite(y); t=t[good]; y=y[good]
    order=np.argsort(t); t=t[order]; y=y[order]
    ends=np.arange(t.min()+hop_s,t.max()+1e-9,hop_s)
    occ=[]
    for end in ends:
        start=max(t.min(),end-window_s)
        m=(t>start)&(t<=end)
        occ.append(100*np.mean(y[m]>threshold_uv) if np.any(m) else np.nan)
    occ=np.asarray(occ)
    candidate=occ>occupancy_threshold_pct
    trigger=np.zeros(len(candidate),dtype=bool); run=0
    for i,v in enumerate(candidate):
        run=run+1 if v else 0
        trigger[i]=run>=persistence
    return pd.DataFrame({'window_end_s':ends,'burst_occupancy_pct':occ,'candidate_on':candidate,'trigger_on':trigger})

def replay_metrics(replay,onset,offset):
    t=replay.window_end_s.to_numpy(float); tr=replay.trigger_on.to_numpy(bool)
    idx=np.flatnonzero(tr & (t>=onset)&(t<=offset))
    return {'trigger_success':bool(idx.size),'latency_s':float(t[idx[0]]-onset) if idx.size else np.nan,
            'first_trigger_s':float(t[idx[0]]) if idx.size else np.nan}

def downsample(df, max_points=25000):
    if len(df)<=max_points: return df
    step=max(1,int(np.ceil(len(df)/max_points)))
    return df.iloc[::step].copy()

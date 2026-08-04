#!/usr/bin/env python3
from pathlib import Path
import argparse, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from skna_framework.io import discover_recordings, read_table

p=argparse.ArgumentParser(description='Check processed recording discovery and optional metadata tables.')
p.add_argument('sources',nargs='*',default=[str(ROOT/'examples'/'001_signals_ecg_skna.csv')])
p.add_argument('--events',default=str(ROOT/'examples'/'example_events.csv'))
p.add_argument('--thresholds',default=str(ROOT/'examples'/'example_thresholds.csv'))
a=p.parse_args()
idx=discover_recordings(a.sources)
print(f'Found {len(idx)} processed recording(s)')
print('Recording IDs:', ', '.join(map(str,idx)) if idx else 'none')
for label,path in [('Events',a.events),('Thresholds',a.thresholds)]:
    table=read_table(path)
    print(f'{label}: {path} — '+('OK' if table is not None and not table.empty else 'MISSING/EMPTY'))

from __future__ import annotations
from pathlib import Path
import re, zipfile
import pandas as pd

SIGNAL_RE = re.compile(r"^(\d+)_signals_ecg_skna\.csv$")

def discover_recordings(sources):
    """Return {pig_id: {'kind': 'csv'|'zip', 'source': Path, 'member': str|None}}."""
    out = {}
    for src in [Path(x).expanduser().resolve() for x in sources if str(x).strip()]:
        if not src.exists():
            continue
        candidates = []
        if src.is_dir():
            candidates.extend(src.rglob("*_signals_ecg_skna.csv"))
            candidates.extend(src.rglob("*.zip"))
        else:
            candidates.append(src)
        for p in candidates:
            if p.suffix.lower() == ".csv":
                m = SIGNAL_RE.match(p.name)
                if m:
                    out[int(m.group(1))] = {"kind":"csv","source":p,"member":None}
            elif p.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(p) as z:
                        for n in z.namelist():
                            m = SIGNAL_RE.match(Path(n).name)
                            if m:
                                out[int(m.group(1))] = {"kind":"zip","source":p,"member":n}
                except zipfile.BadZipFile:
                    pass
    return dict(sorted(out.items()))

def read_recording(entry):
    if entry["kind"] == "csv":
        return pd.read_csv(entry["source"])
    with zipfile.ZipFile(entry["source"]) as z:
        return pd.read_csv(z.open(entry["member"]))

def read_table(path):
    p=Path(path).expanduser()
    if not p.exists(): return None
    return pd.read_csv(p)

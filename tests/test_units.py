import pandas as pd
from pathlib import Path
from skna_framework.analysis import to_uv

def test_processed_example_is_convertible():
    df=pd.read_csv(Path(__file__).parents[1]/"examples/001_signals_ecg_skna.csv")
    y=to_uv(df["skna_med"])
    assert len(y)==len(df)
    assert pd.Series(y).notna().all()

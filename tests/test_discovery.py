from pathlib import Path
from skna_framework.io import discover_recordings

def test_example_discovery():
    root=Path(__file__).parents[1]/"examples"
    found=discover_recordings([str(root)])
    assert len(found)>=1

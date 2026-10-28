"""Packaged build evidence; source runs remain explicitly development builds."""
import json
from pathlib import Path


def build_info():
    path = Path(__file__).parent/'assets/build-info.json'
    return json.loads(path.read_text()) if path.exists() else {'id':'development'}

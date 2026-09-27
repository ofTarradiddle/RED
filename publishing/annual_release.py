"""Publish the validated annual-game edition; raw SEC/price caches stay private."""
import json
from pathlib import Path

from scripts.refresh_annual_game import validate_dataset

ROOT=Path(__file__).resolve().parents[1]


def publish_annual_game(stage, dataset_path=None):
    source=Path(dataset_path or ROOT/'data/annual-game/dataset.json')
    payload=validate_dataset(json.loads(source.read_text()))
    folder=stage/'play';folder.mkdir(exist_ok=True)
    (folder/'data.json').write_text(json.dumps(payload,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n')

"""Publish only the validated, public innovation dataset and service configuration."""
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from scripts.refresh_innovation import validate_dataset

ROOT = Path(__file__).resolve().parents[1]


def publish_innovation(stage, *, dataset_path=None, leaderboard_url=None):
    path = Path(dataset_path or ROOT / 'data/innovation/dataset.json')
    payload = validate_dataset(json.loads(path.read_text()))
    as_of = date.fromisoformat(payload['asOf'])
    if as_of.isoformat() != payload['asOf'] or as_of > datetime.now(timezone.utc).date():
        raise ValueError('Invalid innovation observation cutoff')
    if any(point['date'] > payload['asOf'] for asset in payload['assets'] for point in asset['points']):
        raise ValueError('Innovation quote exceeds published cutoff')
    if any(event['date'] > payload['asOf'] for event in payload['opportunities']):
        raise ValueError('Innovation opportunity exceeds published cutoff')
    url = leaderboard_url if leaderboard_url is not None else os.environ.get('INNOVATION_LEADERBOARD_URL', '')
    if url:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise ValueError('Leaderboard URL must be a public HTTPS service base URL')
    folder = Path(stage) / 'innovation'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'data.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
    (folder / 'config.json').write_text(json.dumps({'leaderboardUrl': url.rstrip('/') if url else None}))

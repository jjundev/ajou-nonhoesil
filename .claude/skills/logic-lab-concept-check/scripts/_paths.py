"""Paths shared by the concept-check commands."""
import sys
from hashlib import sha256
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
REPO = SKILL.parents[2]
ASSETS = SKILL / "assets"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ASSET_HASHES = {
    "review-template.html": "a4ab46b5dd70f6d50748f6b47ffa11a17eb7a7aa4124fb07d2bc06e1b4cbacab",
    "review-interaction.css": "5700e02b9a686b4c2af0b00a3deee81a8531a52c5c1bd2ec5f1e6bb1e44ab37f",
    "review-interaction.js": "654facf47d19f68f4c0e9ed5a87b03333c9d70aedfe17e15353fae22fcbb20f5",
    "review-prompt.js": "344d3a7bc4ffad6eb84c9e2fa6951185de42a6feb28d2ce5a9793d203606ef45",
}


def read_asset(name):
    data = (ASSETS / name).read_bytes()
    if sha256(data).hexdigest() != ASSET_HASHES[name]:
        raise ValueError(f"자구알 원본과 해시가 달라요: {name}")
    return data.decode("utf-8")

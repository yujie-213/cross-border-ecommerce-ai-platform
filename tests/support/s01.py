import json
from pathlib import Path

from commerce_hub.data.sync import FixtureConnector
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture


def example():
    return json.loads((Path(__file__).resolve().parents[2] / "examples/s01_single_sku.json").read_text())


def snapshot(value=None):
    value, batch = FixtureConnector().read(example() if value is None else value)
    return capture(project(value, batch))

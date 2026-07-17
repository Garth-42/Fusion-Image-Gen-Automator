"""Safe deterministic YAML persistence restricted to a manual project root."""
from __future__ import absolute_import

import math
import sys
from pathlib import Path

_VENDOR_ROOT = Path(__file__).resolve().parents[2]
if str(_VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(_VENDOR_ROOT))
import vendor.yaml as yaml

from fmsm.infrastructure.atomic_write import atomic_write_text


class StoreError(ValueError):
    pass


def project_path(root, relative_path):
    root = Path(root).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise StoreError("OUTPUT_PATH_UNSAFE")
    return candidate


def _reject_nonfinite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise StoreError("Non-finite floats cannot be persisted.")
    if isinstance(value, dict):
        for child in value.values():
            _reject_nonfinite(child)
    elif isinstance(value, list):
        for child in value:
            _reject_nonfinite(child)


def dump(data):
    _reject_nonfinite(data)
    return yaml.safe_dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False, indent=2, width=1000000)


def load(path):
    try:
        with Path(path).open("r", encoding="utf-8") as source:
            data = yaml.safe_load(source)
    except (OSError, yaml.YAMLError) as error:
        raise StoreError("YAML_PARSE_FAILED: %s" % error)
    if not isinstance(data, dict):
        raise StoreError("YAML_PARSE_FAILED: Expected a mapping.")
    return data


def write(root, relative_path, data):
    destination = project_path(root, relative_path)
    serialized = dump(data)
    # Parse the serialized payload before touching the destination file.
    try:
        parsed = yaml.safe_load(serialized)
    except yaml.YAMLError as error:
        raise StoreError("YAML_PARSE_FAILED: %s" % error)
    if parsed != data:
        raise StoreError("YAML_PARSE_FAILED: Serialized data did not round-trip.")
    atomic_write_text(destination, serialized)

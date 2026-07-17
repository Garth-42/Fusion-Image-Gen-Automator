import math

import pytest

from fmsm.infrastructure.yaml_store import StoreError, load, write


def test_writes_only_inside_project_root(tmp_path):
    write(tmp_path, "scenes/example.yaml", {"schema_version": 1, "name": "Example"})
    assert load(tmp_path / "scenes/example.yaml")["name"] == "Example"
    with pytest.raises(StoreError, match="OUTPUT_PATH_UNSAFE"):
        write(tmp_path, "../escape.yaml", {"schema_version": 1})


def test_rejects_nonfinite_float(tmp_path):
    with pytest.raises(StoreError, match="Non-finite"):
        write(tmp_path, "scenes/example.yaml", {"value": math.nan})

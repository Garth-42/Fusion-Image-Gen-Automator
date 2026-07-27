"""The palette's inline script is real code that nothing else runs.

Every other palette test matches strings in the document, which cannot tell a
working script from one with a syntax error in it: a broken script still
contains all the right substrings, and the failure only shows up as a palette
frozen on its connecting line inside Fusion. Parse it here instead.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

DOCUMENT = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager" / "ui" / "palette.html"


def _inline_scripts():
    html = DOCUMENT.read_text(encoding="utf-8")
    return re.findall(r"<script>(.*?)</script>", html, re.S)


def test_the_document_has_exactly_one_inline_script():
    # The extraction below, and the add-in's whole page-side behaviour, assume a
    # single script block. A second one would silently go unchecked.
    assert len(_inline_scripts()) == 1


def test_the_palette_script_parses(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is unavailable; CI runs this check")

    script = tmp_path / "palette.js"
    script.write_text(_inline_scripts()[0], encoding="utf-8")

    result = subprocess.run(
        [node, "--check", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert result.returncode == 0, result.stdout.decode("utf-8", "replace")


def test_the_palette_script_avoids_syntax_the_fusion_browser_may_not_have():
    # The palette runs in Fusion's embedded browser, which has been both CEF and
    # Qt WebEngine across supported versions. The existing script is written in
    # conservative ES5 for that reason -- var, function expressions, no arrow
    # functions -- and a stray modern construct would parse fine under node's
    # check above while failing on an older host.
    script = _inline_scripts()[0]
    # Strip comments and string literals first: prose in a comment ("... => ...")
    # and text in a message must not be mistaken for code.
    without_block_comments = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    code = re.sub(r"^\s*//.*$", "", without_block_comments, flags=re.M)
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)
    code = re.sub(r"'(?:[^'\\]|\\.)*'", "''", code)

    assert "=>" not in code, "arrow functions are newer than the oldest supported host"
    assert not re.search(r"\bconst\b|\blet\b", code), "use var, as the rest of the script does"
    assert "`" not in code, "template literals are newer than the oldest supported host"

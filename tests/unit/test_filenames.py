from fmsm.domain.filenames import scene_basename, slugify


def test_slug_and_basename_are_stable():
    assert slugify("Install Left DIN Rail!") == "install-left-din-rail"
    assert slugify("日本語") == "scene"
    assert scene_basename("New title", "78b36cd7-532e-4d82-b8d7-b04ccbfa73ae") == "new-title__78b36cd7"

"""Tests of ``tools/build_packages.py``."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from tools import build_packages

DEMO_PYPROJECT = """\
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-pkg"
version = "1.0.0"

[tool.setuptools]
py-modules = ["demo"]
"""


def test_sdist_normalization_is_deterministic(tmp_path: Path) -> None:
    def make(path: Path, mtime: int) -> None:
        with tarfile.open(path, "w:gz") as archive:
            for name in ("pkg/b.txt", "pkg/a.txt"):
                data = name.encode()
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.uid, info.uname = len(data), mtime, 1000, "someone"
                archive.addfile(info, io.BytesIO(data))

    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    make(first, 1)
    make(second, 999_999)
    for path in (first, second):
        build_packages.normalize_sdist(path, "1794441600")
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        assert [member.name for member in archive.getmembers()] == ["pkg/a.txt", "pkg/b.txt"]
        assert {member.mtime for member in archive.getmembers()} == {1794441600}


def test_rebuilding_into_a_folder_with_artifacts_replaces_them(tmp_path: Path) -> None:
    project, out = tmp_path / "demo", tmp_path / "out"
    project.mkdir()
    (project / "pyproject.toml").write_text(DEMO_PYPROJECT, encoding="utf-8")
    (project / "demo.py").write_text('"""Demo."""\n', encoding="utf-8")
    first = build_packages.build_project(project, out, "1794441600")
    hashes = {path.name: build_packages.sha256(path) for path in first}
    second = build_packages.build_project(project, out, "1794441600")
    assert [path.name for path in second] == [path.name for path in first]
    assert {path.name: build_packages.sha256(path) for path in second} == hashes
    wheel_only = build_packages.build_project(
        project, tmp_path / "wheels", "1794441600", sdist=False
    )
    assert [path.suffix for path in wheel_only] == [".whl"]
    assert not (project / "build").exists()


def test_a_failed_build_shows_its_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "broken"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 1\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="build failed"):
        build_packages.build_project(project, tmp_path / "out", "1794441600")
    assert capsys.readouterr().err

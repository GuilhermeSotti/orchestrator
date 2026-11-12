"""Build the wheel and the sdist of every package, reproducibly.

Usage::

    python tools/build_packages.py                     # build into dist/
    python tools/build_packages.py --check             # build twice and compare SHA-256
    python tools/build_packages.py --package orchestrator-core --out dist

The build uses the setuptools installed in the current environment (pinned in
``requirements/dev.txt``), without build isolation, and a fixed
``SOURCE_DATE_EPOCH`` taken from the last commit (or a constant outside Git).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("orchestrator-core",)
DEFAULT_EPOCH = "1794441600"  # 2026-11-12T00:00:00Z, used when Git is unavailable

_BUILD = (  # setuptools rewrites sys.argv during a build: read the arguments first
    "import sys\n"
    "out, kinds = sys.argv[1], sys.argv[2].split(',')\n"
    "from setuptools import build_meta\n"
    "if 'sdist' in kinds:\n"
    "    build_meta.build_sdist(out)\n"
    "if 'wheel' in kinds:\n"
    "    build_meta.build_wheel(out)\n"
)
_IGNORED = shutil.ignore_patterns(
    "__pycache__", "*.egg-info", "build", "dist", ".pytest_cache", "tests"
)


def source_date_epoch() -> str:
    """Return the commit time of HEAD, or a constant outside a Git checkout."""
    if "SOURCE_DATE_EPOCH" in os.environ:
        return os.environ["SOURCE_DATE_EPOCH"]
    git = shutil.which("git")
    if git is None:
        return DEFAULT_EPOCH
    result = subprocess.run(  # noqa: S603 - fixed arguments, no shell
        [git, "log", "-1", "--format=%ct"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value.isdigit() else DEFAULT_EPOCH


def build(package: str, out: Path, epoch: str) -> list[Path]:
    """Build the wheel and the sdist of one package of ``packages/`` into ``out``."""
    source = ROOT / "packages" / package
    if not (source / "pyproject.toml").is_file():
        msg = f"unknown package: {package}"
        raise SystemExit(msg)
    return build_project(source, out, epoch)


def build_project(source: Path, out: Path, epoch: str, *, sdist: bool = True) -> list[Path]:
    """Build the project at ``source`` into ``out`` and return the produced artifacts.

    The project is copied to a temporary folder (without tests and build
    leftovers) and built there, so the source tree is never modified. Existing
    artifacts with the same name in ``out`` are replaced.
    """
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"build-{source.name}-") as staging:
        work, built = Path(staging) / "project", Path(staging) / "artifacts"
        shutil.copytree(source, work, ignore=_IGNORED)
        built.mkdir()
        env = {**os.environ, "SOURCE_DATE_EPOCH": epoch, "PYTHONHASHSEED": "0"}
        kinds = "sdist,wheel" if sdist else "wheel"
        try:
            subprocess.run(  # noqa: S603 - fixed interpreter and script
                [sys.executable, "-c", _BUILD, str(built), kinds],
                cwd=work,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            sys.stderr.write(exc.stdout + exc.stderr)
            msg = f"build failed: {source}"
            raise SystemExit(msg) from None
        produced = []
        for artifact in sorted(built.iterdir()):
            if artifact.name.endswith(".tar.gz"):
                normalize_sdist(artifact, epoch)
            target = out / artifact.name
            shutil.copyfile(artifact, target)
            produced.append(target)
    return produced


def normalize_sdist(path: Path, epoch: str) -> None:
    """Rewrite an sdist deterministically: sorted members, fixed times, owners and modes.

    setuptools does not apply ``SOURCE_DATE_EPOCH`` to the gzip header nor to
    generated files, so the archive is normalized after the build.
    """
    timestamp = int(epoch)
    with tarfile.open(path, "r:gz") as source:
        members = []
        for info in source.getmembers():
            extracted = source.extractfile(info) if info.isfile() else None
            members.append((info, extracted.read() if extracted is not None else None))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as target:
        for info, data in sorted(members, key=lambda item: item[0].name):
            info.mtime = timestamp
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if info.isdir() else 0o644
            info.pax_headers = {}
            target.addfile(info, io.BytesIO(data) if data is not None else None)
    with path.open("wb") as handle, gzip.GzipFile("", "wb", 9, handle, mtime=timestamp) as gz:
        gz.write(buffer.getvalue())


def sha256(path: Path) -> str:
    """Return the SHA-256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    """Build the packages; with --check, build twice and compare the hashes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package", action="append", choices=PACKAGES, help="package to build")
    parser.add_argument("--out", default=str(ROOT / "dist"), help="output folder")
    parser.add_argument("--check", action="store_true", help="build twice and compare hashes")
    args = parser.parse_args(argv)
    packages = tuple(args.package or PACKAGES)
    epoch = source_date_epoch()
    out = Path(args.out)
    artifacts = [artifact for package in packages for artifact in build(package, out, epoch)]
    lines = [f"{sha256(path)}  {path.name}" for path in artifacts]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.write("\n".join(lines) + "\n")
    if not args.check:
        return 0
    with tempfile.TemporaryDirectory(prefix="rebuild-") as again:
        second = {
            path.name: sha256(path)
            for package in packages
            for path in build(package, Path(again), epoch)
        }
    mismatches = [path.name for path in artifacts if second.get(path.name) != sha256(path)]
    if mismatches:
        sys.stderr.write(f"not reproducible: {', '.join(mismatches)}\n")
        return 1
    sys.stdout.write(f"reproducible: {len(artifacts)} artifacts, SOURCE_DATE_EPOCH={epoch}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

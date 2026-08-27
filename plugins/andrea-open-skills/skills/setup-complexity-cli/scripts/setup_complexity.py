#!/usr/bin/env python3
"""Install a pinned Complexity CLI release after explicit user approval."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_VERSION = "0.4.0"
REPOSITORY = "andrea-sdl/complexity-evaluator"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the Complexity CLI.")
    parser.add_argument("--check", action="store_true", help="Check without installing")
    parser.add_argument("--install-dir", type=Path, help="Override the install directory")
    return parser.parse_args()


def target() -> str:
    systems = {"Darwin": "apple-darwin", "Linux": "unknown-linux-gnu"}
    machines = {
        "arm64": "aarch64",
        "aarch64": "aarch64",
        "x86_64": "x86_64",
        "AMD64": "x86_64",
    }
    system = platform.system()
    machine = machines.get(platform.machine())
    if system == "Windows" and machine == "x86_64":
        return "x86_64-pc-windows-msvc"
    if system in systems and machine:
        return f"{machine}-{systems[system]}"
    raise RuntimeError(f"unsupported platform: {system} {platform.machine()}")


def install_directory() -> Path:
    if platform.system() == "Windows":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return root / "andrea-open-skills" / "bin"


def binary_name() -> str:
    return "complexity.exe" if platform.system() == "Windows" else "complexity"


def binary_version(binary: Path) -> str | None:
    if not binary.is_file():
        return None
    try:
        result = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    prefix = "complexity "
    output = result.stdout.strip()
    return output[len(prefix) :] if result.returncode == 0 and output.startswith(prefix) else None


def candidate_binary(destination: Path, version: str) -> Path | None:
    managed = destination / binary_name()
    if binary_version(managed) == version:
        return managed
    existing = shutil.which("complexity")
    if existing and binary_version(Path(existing)) == version:
        return Path(existing)
    return None


def asset_details(version: str) -> tuple[str, str]:
    release_target = target()
    suffix = ".zip" if platform.system() == "Windows" else ".tar.gz"
    return release_target, f"complexity-{version}-{release_target}{suffix}"


def download(url: str, destination: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            destination.write_bytes(response.read())
    except (OSError, urllib.error.URLError) as error:
        raise RuntimeError(f"download failed: {url}: {error}") from error


def download_release(version: str, asset: str, destination: Path) -> None:
    github = shutil.which("gh")
    if github:
        result = subprocess.run(
            [
                github,
                "release",
                "download",
                f"complexity-v{version}",
                "--repo",
                REPOSITORY,
                "--pattern",
                asset,
                "--pattern",
                f"{asset}.sha256",
                "--dir",
                str(destination),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
    base = f"https://github.com/{REPOSITORY}/releases/download/complexity-v{version}"
    download(f"{base}/{asset}", destination / asset)
    download(f"{base}/{asset}.sha256", destination / f"{asset}.sha256")


def verify_checksum(archive: Path, checksum: Path) -> None:
    parts = checksum.read_text(encoding="utf-8").strip().split()
    if len(parts) != 2 or parts[1] != archive.name:
        raise RuntimeError("release checksum file is invalid")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != parts[0].lower():
        raise RuntimeError("release checksum does not match the archive")


def binary_bytes(archive: Path, expected_name: str) -> bytes:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as release:
            names = [
                name
                for name in release.namelist()
                if PurePosixPath(name).name == expected_name
            ]
            if len(names) != 1:
                raise RuntimeError("release archive must contain one executable")
            return release.read(names[0])
    with tarfile.open(archive, mode="r:gz") as release:
        members = [
            member
            for member in release.getmembers()
            if member.isfile() and PurePosixPath(member.name).name == expected_name
        ]
        if len(members) != 1:
            raise RuntimeError("release archive must contain one executable")
        source = release.extractfile(members[0])
        if source is None:
            raise RuntimeError("release executable cannot be read")
        return source.read()


def install(version: str, destination: Path) -> Path:
    release_target, asset = asset_details(version)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        archive = temporary_root / asset
        checksum = temporary_root / f"{asset}.sha256"
        download_release(version, asset, temporary_root)
        verify_checksum(archive, checksum)
        executable_name = "complexity.exe" if "windows" in release_target else "complexity"
        executable = destination / executable_name
        staged = destination / f".{executable.name}.new"
        staged.write_bytes(binary_bytes(archive, executable.name))
        staged.chmod(staged.stat().st_mode | stat.S_IXUSR)
        staged.replace(executable)
    if binary_version(executable) != version:
        raise RuntimeError("installed executable did not report the requested version")
    return executable


def main() -> int:
    args = parse_args()
    destination = args.install_dir.expanduser() if args.install_dir else install_directory()
    ready = candidate_binary(destination, DEFAULT_VERSION)
    if ready:
        print(f"READY complexity {DEFAULT_VERSION}: {ready}")
        return 0
    if args.check:
        print(f"SETUP_REQUIRED complexity {DEFAULT_VERSION}: {destination / binary_name()}")
        return 1
    try:
        executable = install(DEFAULT_VERSION, destination)
    except RuntimeError as error:
        print(f"SETUP_FAILED complexity {DEFAULT_VERSION}: {error}", file=sys.stderr)
        return 2
    print(f"INSTALLED complexity {DEFAULT_VERSION}: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

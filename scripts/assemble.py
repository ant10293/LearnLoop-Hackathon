#!/usr/bin/env python3
"""Assemble LearnLoop from the pinned vision-test-bench commit plus this repository's overlay.

    python3 scripts/assemble.py                      # fetch the dependency from GitHub
    python3 scripts/assemble.py --dependency ../vision-test-bench   # or from a local clone

Steps, each checked against overlay/manifest.json:

  1. Fetch vision-test-bench at the pinned commit into build/deps/ (Git-ignored) and confirm
     both the commit and its tree hash.
  2. Export that commit's files (no Git history) into a fresh staging directory.
  3. Delete the files the hackathon removed, after checking each one's SHA-256.
  4. Apply overlay/edits/*.edits to the files the hackathon changed.
  5. Copy overlay/files/* (files created during the hackathon).
  6. Set file modes and verify that every file in the result has the expected SHA-256 and mode
     and that no other file exists.
  7. Swap the staging directory into place at build/LearnLoop, carrying over local state from a
     previous assembly (backend/.venv, frontend/node_modules, data/, .env) so a rebuild never
     discards a database or an installed environment.

Edit script format (overlay/edits/<path>.edits)
------------------------------------------------
Lines starting with '#' before the first hunk are headers (path, base-sha256, result-sha256).
Each hunk starts with

    @@ -A,B +C,D @@

meaning: replace B lines of the dependency's file starting at line A (1-based) with the D lines
that follow, each prefixed with '+'. When B is 0 the new lines go after line A. This is the hunk
header of `git diff -U0`; the '-' lines, context lines and function headers are omitted so that
no pre-kickoff text is stored in this repository. A '\\ No newline at end of file' line after a
'+' line means that line has no trailing newline. Hunks are applied in order, and the result
must match result-sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "overlay"
BUILD = ROOT / "build"
HUNK = re.compile(rb"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n$")
# Local, Git-ignored state inside an assembled tree that a rebuild keeps.
PRESERVE = ["backend/.venv", "frontend/node_modules", "data", ".env"]


class AssemblyError(Exception):
    pass


def log(msg: str) -> None:
    print(f"[assemble] {msg}", flush=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(*args: str, cwd: Path | None = None) -> bytes:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if proc.returncode != 0:
        raise AssemblyError(f"git {' '.join(args)} failed:\n{proc.stderr.decode(errors='replace')}")
    return proc.stdout


def fetch_dependency(dep: dict, source: str) -> Path:
    """Shallow-fetch the pinned commit into build/deps/<name>. Returns that Git directory."""
    repo = BUILD / "deps" / dep["name"]
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        run_git("init", "-q", cwd=repo)
    have = subprocess.run(["git", "cat-file", "-e", dep["commit"] + "^{commit}"], cwd=repo, capture_output=True)
    if have.returncode != 0:
        url = source
        if Path(source).exists():
            url = Path(source).resolve().as_uri()
        log(f"fetching {dep['name']} {dep['commit'][:12]} from {source}")
        run_git("fetch", "-q", "--depth", "1", "--no-tags", url, dep["commit"], cwd=repo)
    tree = run_git("rev-parse", dep["commit"] + "^{tree}", cwd=repo).decode().strip()
    if tree != dep["tree"]:
        raise AssemblyError(f"{dep['name']} {dep['commit']} has tree {tree}, expected {dep['tree']}")
    log(f"{dep['name']} @ {dep['commit'][:12]} verified (tree {tree[:12]})")
    return repo


def export_commit(repo: Path, commit: str, dest: Path) -> None:
    data = run_git("archive", "--format=tar", commit, cwd=repo)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(dest, filter="data")
        else:  # Python < 3.11.4; the archive comes from a verified commit
            tar.extractall(dest)


def apply_edits(original: bytes, script: bytes, rel: str) -> bytes:
    lines = script.splitlines(keepends=True)
    headers: dict[str, str] = {}
    i = 0
    while i < len(lines) and lines[i].startswith(b"#"):
        key, _, value = lines[i][1:].decode().strip().partition(":")
        headers[key.strip()] = value.strip()
        i += 1
    if headers.get("path") != rel:
        raise AssemblyError(f"{rel}: edit script names {headers.get('path')!r}")
    if sha256_bytes(original) != headers.get("base-sha256"):
        raise AssemblyError(f"{rel}: dependency file does not match base-sha256")

    base = original.splitlines(keepends=True)
    out: list[bytes] = []
    cursor = 0  # next base line (0-based) not yet copied
    while i < len(lines):
        m = HUNK.match(lines[i])
        if not m:
            raise AssemblyError(f"{rel}: expected a hunk header, got {lines[i]!r}")
        a, b, _c, d = (int(x) for x in m.groups())
        i += 1
        start = a if b == 0 else a - 1  # 0-based index of the first replaced line
        if start < cursor or start + b > len(base):
            raise AssemblyError(f"{rel}: hunk -{a},{b} is out of order or out of range")
        out.extend(base[cursor:start])
        cursor = start + b
        for _ in range(d):
            if i >= len(lines) or not lines[i].startswith(b"+"):
                raise AssemblyError(f"{rel}: hunk -{a},{b} is missing added lines")
            new = lines[i][1:]
            i += 1
            if i < len(lines) and lines[i].startswith(b"\\"):
                new = new[:-1] if new.endswith(b"\n") else new
                i += 1
            out.append(new)
    out.extend(base[cursor:])
    result = b"".join(out)
    if sha256_bytes(result) != headers.get("result-sha256"):
        raise AssemblyError(f"{rel}: result does not match result-sha256")
    return result


def prune_empty_dirs(top: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(top, topdown=False):
        p = Path(dirpath)
        if p != top and not any(p.iterdir()):
            p.rmdir()


def list_files(top: Path) -> set[str]:
    found = set()
    for dirpath, _dirnames, filenames in os.walk(top):
        for name in filenames:
            found.add(Path(dirpath, name).relative_to(top).as_posix())
    return found


def assemble(manifest: dict, dep_repo: Path, out: Path) -> None:
    files: dict[str, dict] = manifest["files"]
    deleted: dict[str, str] = manifest["deleted"]
    stage = out.with_name(out.name + ".staging")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    export_commit(dep_repo, manifest["dependency"]["commit"], stage)

    base_files = list_files(stage)
    expected_base = {p for p, e in files.items() if e["action"] in ("keep", "edit")} | set(deleted)
    if base_files != expected_base:
        extra, missing = sorted(base_files - expected_base), sorted(expected_base - base_files)
        raise AssemblyError(f"dependency file list differs from manifest: extra={extra[:5]} missing={missing[:5]}")

    for rel, digest in sorted(deleted.items()):
        p = stage / rel
        if sha256_bytes(p.read_bytes()) != digest:
            raise AssemblyError(f"{rel}: file to delete does not match its recorded hash")
        p.unlink()
    prune_empty_dirs(stage)

    for rel, entry in sorted(files.items()):
        p = stage / rel
        if entry["action"] == "keep":
            if sha256_bytes(p.read_bytes()) != entry["base_sha256"]:
                raise AssemblyError(f"{rel}: unchanged dependency file does not match its hash")
        elif entry["action"] == "edit":
            script = (OVERLAY / "edits" / (rel + ".edits")).read_bytes()
            p.write_bytes(apply_edits(p.read_bytes(), script, rel))
        elif entry["action"] == "add":
            if p.exists():
                raise AssemblyError(f"{rel}: new file already exists in the dependency")
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OVERLAY / "files" / rel, p)
        else:
            raise AssemblyError(f"{rel}: unknown action {entry['action']!r}")
        p.chmod(0o755 if entry["mode"] == "100755" else 0o644)

    # Full verification of the result.
    result = list_files(stage)
    if result != set(files):
        raise AssemblyError(f"result file list differs: extra={sorted(result - set(files))[:5]} "
                            f"missing={sorted(set(files) - result)[:5]}")
    for rel, entry in files.items():
        p = stage / rel
        if sha256_bytes(p.read_bytes()) != entry["sha256"]:
            raise AssemblyError(f"{rel}: result does not match its recorded hash")
        executable = bool(p.stat().st_mode & stat.S_IXUSR)
        if executable != (entry["mode"] == "100755"):
            raise AssemblyError(f"{rel}: wrong file mode")
    log(f"verified {len(files)} files against the manifest "
        f"({manifest['counts']['add']} new, {manifest['counts']['edit']} edited, "
        f"{manifest['counts']['keep']} unchanged from the dependency, {manifest['counts']['delete']} removed)")

    if out.exists():
        for rel in PRESERVE:
            if (out / rel).exists() or (out / rel).is_symlink():
                (stage / rel).parent.mkdir(parents=True, exist_ok=True)
                os.replace(out / rel, stage / rel)
                log(f"kept {rel} from the previous assembly")
        shutil.rmtree(out)
    os.replace(stage, out)
    log(f"LearnLoop assembled at {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dependency", help="URL or local path of vision-test-bench (default: manifest URL)")
    ap.add_argument("--out", type=Path, default=BUILD / "LearnLoop", help="output directory (default: build/LearnLoop)")
    args = ap.parse_args()

    manifest = json.loads((OVERLAY / "manifest.json").read_text())
    dep = manifest["dependency"]
    try:
        repo = fetch_dependency(dep, args.dependency or dep["url"])
        assemble(manifest, repo, args.out.resolve())
    except AssemblyError as exc:
        print(f"[assemble] FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

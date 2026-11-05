#!/usr/bin/env python3
"""Regenerate overlay/ from the two pinned commits. Maintainer tool, not needed to run LearnLoop.

    python3 scripts/generate_overlay.py \
        --dependency-repo ../vision-test-bench --reference-repo ../LearnLoop

It compares vision-test-bench at the pinned pre-kickoff commit (the external dependency) with
LearnLoop at the audited commit, and writes:

  overlay/files/<path>          complete files that do not exist in the dependency
  overlay/edits/<path>.edits    insertion-only edit scripts for files the hackathon changed
  overlay/manifest.json         every path in the result, with hashes, modes and actions

Edit scripts never contain pre-kickoff text: each hunk names the dependency lines it replaces
by number only and carries only the new lines. See scripts/assemble.py for the format.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "overlay"

DEPENDENCY = {
    "name": "vision-test-bench",
    "url": "https://github.com/ant10293/vision-test-bench.git",
    "commit": "27859ac787ae214862488d6348898d012d57353c",
}
REFERENCE = {
    "name": "LearnLoop",
    "url": "https://github.com/ant10293/LearnLoop.git",
    "commit": "00a03401162de79ce5e4a0ce5acb79134772f581",
}

HUNK = re.compile(rb"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def tree_of(repo: Path, commit: str) -> dict[str, str]:
    """path -> mode for every blob in the commit."""
    out = {}
    for line in git(repo, "ls-tree", "-r", "-z", commit).split(b"\0"):
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        mode, kind, _ = meta.split(b" ")
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            sys.exit(f"unsupported entry {path!r} ({mode.decode()} {kind.decode()})")
        out[path.decode()] = mode.decode()
    return out


def export(repo: Path, commit: str, dest: Path) -> None:
    data = git(repo, "archive", "--format=tar", commit)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, filter="data")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edit_script(base: Path, target: Path, rel: str) -> bytes:
    """git -U0 diff with removed lines, context and function headers dropped."""
    proc = subprocess.run(
        ["git", "diff", "--no-index", "--no-color", "-U0", "--histogram", "--no-ext-diff",
         "--", str(base), str(target)],
        capture_output=True,
    )
    if proc.returncode not in (0, 1):
        sys.exit(proc.stderr.decode())
    out = [
        b"# LearnLoop hackathon edit script v1\n",
        b"# path: " + rel.encode() + b"\n",
        b"# base-sha256: " + sha256(base).encode() + b"\n",
        b"# result-sha256: " + sha256(target).encode() + b"\n",
    ]
    in_hunk = False
    last = None  # "+" or "-": which side the previous body line belonged to
    for line in proc.stdout.splitlines(keepends=True):
        m = HUNK.match(line)
        if m:
            a, b, c, d = (m.group(i) for i in range(1, 5))
            b = b if b is not None else b"1"
            d = d if d is not None else b"1"
            out.append(b"@@ -%s,%s +%s,%s @@\n" % (a, b, c, d))
            in_hunk, last = True, None
        elif not in_hunk:
            continue  # file headers
        elif line.startswith(b"+"):
            out.append(line)
            last = "+"
        elif line.startswith(b"-"):
            last = "-"  # pre-kickoff text: dropped, the hunk header carries its line range
        elif line.startswith(b"\\"):
            if last == "+":
                out.append(b"\\ No newline at end of file\n")
        else:
            sys.exit(f"unexpected diff line in {rel}: {line!r}")
    return b"".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dependency-repo", type=Path, required=True)
    ap.add_argument("--reference-repo", type=Path, required=True)
    args = ap.parse_args()

    base_modes = tree_of(args.dependency_repo, DEPENDENCY["commit"])
    target_modes = tree_of(args.reference_repo, REFERENCE["commit"])

    with tempfile.TemporaryDirectory() as tmp:
        base_dir, target_dir = Path(tmp, "base"), Path(tmp, "target")
        export(args.dependency_repo, DEPENDENCY["commit"], base_dir)
        export(args.reference_repo, REFERENCE["commit"], target_dir)

        if OVERLAY.exists():
            shutil.rmtree(OVERLAY)
        (OVERLAY / "files").mkdir(parents=True)
        (OVERLAY / "edits").mkdir(parents=True)

        files: dict[str, dict] = {}
        for rel in sorted(target_modes):
            t = target_dir / rel
            entry = {"mode": target_modes[rel], "sha256": sha256(t)}
            if rel not in base_modes:
                entry["action"] = "add"
                dest = OVERLAY / "files" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(t, dest)
            else:
                b = base_dir / rel
                entry["base_sha256"] = sha256(b)
                entry["base_mode"] = base_modes[rel]
                if entry["base_sha256"] == entry["sha256"]:
                    entry["action"] = "keep"
                else:
                    entry["action"] = "edit"
                    dest = OVERLAY / "edits" / (rel + ".edits")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(edit_script(b, t, rel))
            files[rel] = entry

        deleted = {rel: sha256(base_dir / rel) for rel in sorted(base_modes) if rel not in target_modes}

    dependency = dict(DEPENDENCY, tree=git(args.dependency_repo, "rev-parse", DEPENDENCY["commit"] + "^{tree}").decode().strip(),
                      committed=git(args.dependency_repo, "show", "-s", "--format=%cI", DEPENDENCY["commit"]).decode().strip())
    reference = dict(REFERENCE, tree=git(args.reference_repo, "rev-parse", REFERENCE["commit"] + "^{tree}").decode().strip(),
                     committed=git(args.reference_repo, "show", "-s", "--format=%cI", REFERENCE["commit"]).decode().strip())
    counts = {k: sum(1 for e in files.values() if e["action"] == k) for k in ("add", "edit", "keep")}
    counts["delete"] = len(deleted)
    manifest = {
        "format": 1,
        "dependency": dependency,
        "reference": reference,
        "counts": counts,
        "files": files,
        "deleted": deleted,
    }
    (OVERLAY / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_file_list(manifest)
    print(json.dumps(counts))


def edit_stats(rel: str) -> tuple[int, int]:
    """(lines added, dependency lines replaced or removed) for one edit script."""
    added = removed = 0
    for line in (OVERLAY / "edits" / (rel + ".edits")).read_bytes().splitlines():
        m = HUNK.match(line)
        if m:
            removed += int(m.group(2))
        elif line.startswith(b"+"):
            added += 1
    return added, removed


def write_file_list(manifest: dict) -> None:
    files, deleted = manifest["files"], manifest["deleted"]
    dep, ref = manifest["dependency"], manifest["reference"]
    out = [
        "# File-level migration plan",
        "",
        "Generated by `scripts/generate_overlay.py`. Do not edit by hand.",
        "",
        f"Baseline (external dependency): {dep['name']} `{dep['commit']}` ({dep['committed']}).  ",
        f"Result: {ref['name']} `{ref['commit']}` ({ref['committed']}).",
        "",
        "| Action | Files | Stored in this repository |",
        "| --- | ---: | --- |",
    ]
    c = manifest["counts"]
    out += [
        f"| Created during the hackathon | {c['add']} | complete file in `overlay/files/` |",
        f"| Pre-existing, changed during the hackathon | {c['edit']} | insertion-only edit script in `overlay/edits/` |",
        f"| Pre-existing, unchanged | {c['keep']} | nothing; taken from the dependency and hash-checked |",
        f"| Pre-existing, removed during the hackathon | {c['delete']} | path and hash in `overlay/manifest.json` |",
        "",
    ]
    new_lines = sum((OVERLAY / "files" / p).read_bytes().count(b"\n") for p, e in files.items() if e["action"] == "add")
    stats = {p: edit_stats(p) for p, e in files.items() if e["action"] == "edit"}
    out += [
        f"New files hold {new_lines:,} lines. Edit scripts add {sum(a for a, _ in stats.values()):,} lines and "
        f"replace or remove {sum(r for _, r in stats.values()):,} dependency lines, identified by line number only.",
        "",
        "## Created during the hackathon",
        "",
        "| File | Lines |",
        "| --- | ---: |",
    ]
    def count_lines(p: str) -> int:
        return (OVERLAY / "files" / p).read_bytes().count(b"\n")

    out += [f"| `{p}` | {count_lines(p):,} |" for p, e in sorted(files.items()) if e["action"] == "add"]
    out += ["", "## Changed during the hackathon", "", "| File | Lines added | Dependency lines replaced or removed |",
            "| --- | ---: | ---: |"]
    out += [f"| `{p}` | {stats[p][0]:,} | {stats[p][1]:,} |" for p in sorted(stats)]
    out += ["", "## Unchanged from the dependency", ""]
    out += [f"- `{p}`" for p, e in sorted(files.items()) if e["action"] == "keep"]
    out += ["", "## Removed during the hackathon", "",
            "Research-only code from vision-test-bench that LearnLoop does not run: non-Meta providers, the research UI, "
            "and the tracking, recovery, evaluation, audio and demo-scenario modules.", ""]
    out += [f"- `{p}`" for p in sorted(deleted)]
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "FILES.md").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()

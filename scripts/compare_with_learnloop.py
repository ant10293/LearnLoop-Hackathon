#!/usr/bin/env python3
"""Check that a fresh assembly is byte-for-byte identical to LearnLoop at the audited commit.

    python3 scripts/compare_with_learnloop.py                  # fetch LearnLoop from GitHub
    python3 scripts/compare_with_learnloop.py --reference ../LearnLoop

This does not trust overlay/manifest.json. It assembles into build/compare/assembled, exports a
clean `git archive` of LearnLoop at the pinned commit into build/compare/reference, and compares
the two trees file by file: the same paths, the same bytes, and the same executable bits.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble  # noqa: E402

COMPARE = assemble.BUILD / "compare"


def tree(top: Path) -> dict[str, tuple[bytes, bool]]:
    out = {}
    for dirpath, _dirs, names in os.walk(top):
        for name in names:
            p = Path(dirpath, name)
            out[p.relative_to(top).as_posix()] = (p.read_bytes(), bool(p.stat().st_mode & stat.S_IXUSR))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", help="URL or local path of LearnLoop (default: manifest URL)")
    ap.add_argument("--dependency", help="URL or local path of vision-test-bench (default: manifest URL)")
    args = ap.parse_args()

    manifest = json.loads((assemble.OVERLAY / "manifest.json").read_text())
    ref = manifest["reference"]
    if COMPARE.exists():
        shutil.rmtree(COMPARE)
    COMPARE.mkdir(parents=True)

    try:
        dep_repo = assemble.fetch_dependency(manifest["dependency"], args.dependency or manifest["dependency"]["url"])
        assemble.assemble(manifest, dep_repo, COMPARE / "assembled")
        ref_repo = assemble.fetch_dependency(ref, args.reference or ref["url"])
        (COMPARE / "reference").mkdir()
        assemble.export_commit(ref_repo, ref["commit"], COMPARE / "reference")
    except assemble.AssemblyError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    built, want = tree(COMPARE / "assembled"), tree(COMPARE / "reference")
    problems = []
    problems += [f"missing from assembly: {p}" for p in sorted(set(want) - set(built))]
    problems += [f"not in LearnLoop: {p}" for p in sorted(set(built) - set(want))]
    for p in sorted(set(want) & set(built)):
        if built[p][0] != want[p][0]:
            problems.append(f"content differs: {p}")
        if built[p][1] != want[p][1]:
            problems.append(f"executable bit differs: {p}")

    # Cross-check the file list against Git's own index of the commit (catches anything
    # `git archive` might skip, such as export-ignore attributes).
    listed = set(subprocess.run(["git", "ls-tree", "-r", "--name-only", "-z", ref["commit"]],
                                cwd=ref_repo, check=True, capture_output=True).stdout.decode().split("\0")) - {""}
    if listed != set(want):
        problems.append("git ls-tree and git archive disagree on the LearnLoop file list")

    total = sum(len(v[0]) for v in want.values())
    if problems:
        print(f"MISMATCH: {len(problems)} problem(s)")
        for line in problems[:50]:
            print("  " + line)
        return 1
    print(f"MATCH: {len(want)} files, {total:,} bytes identical to {ref['name']} "
          f"{ref['commit']} (tree {ref['tree']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

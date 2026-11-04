# Submission provenance

How this repository was produced, what it contains, and the evidence for each date.

## Timeline

| Event | When | Evidence |
| --- | --- | --- |
| vision-test-bench created | 2026-10-23 02:05 UTC | [evidence/repositories.txt](evidence/repositories.txt) |
| Pinned dependency commit `27859ac` pushed to GitHub | 2026-10-26 07:29:48 UTC (03:29 AM ET) | [evidence/vision-test-bench-push-activity.txt](evidence/vision-test-bench-push-activity.txt), from GitHub's server-side activity log |
| Hackathon kickoff | 2026-10-26 16:00 UTC (12:00 PM ET) | Official schedule |
| Next vision-test-bench push, after kickoff | 2026-10-26 16:29:47 UTC (12:29 PM ET) | Same activity log |
| LearnLoop repository created | 2026-10-29 05:27 UTC | [evidence/repositories.txt](evidence/repositories.txt) |
| vision-test-bench `386cba7` imported into LearnLoop (`2babd11`) | 2026-11-02 | LearnLoop history |
| LearnLoop `8e718cc` pushed (the audited result) | 2026-11-04 20:19 UTC | LearnLoop activity log |
| This repository created | 2026-11-04 20:57 UTC | [evidence/repositories.txt](evidence/repositories.txt) |

Commit timestamps are recorded by the author's machine. The push times above come from GitHub, and they bracket kickoff: `27859ac` was on GitHub 8.5 hours before kickoff, and nothing was pushed between it and kickoff.

## The baseline

The baseline is vision-test-bench at `27859ac787ae214862488d6348898d012d57353c` (tree `aee613efe64817a55c82179eafe8dc6f94558413`), its last commit before kickoff. Everything after it, including the 77 vision-test-bench commits made during the hackathon between 2026-10-26 and 2026-11-02, is treated as hackathon work and stored in this repository's overlay. The result was compared against LearnLoop `8e718ccc49e63bfb5443c77554d98c685818b6e5` (tree `9ab0296b9a52a9dea12030f98483df5a04f6ca87`).

## What this repository contains

- `overlay/files/`: 71 complete files that do not exist at the baseline commit.
- `overlay/edits/`: 66 edit scripts. Each holds only the lines added during the hackathon and the line numbers they replace. No context lines, removed lines, or function headers are stored.
- `overlay/manifest.json`: the dependency's URL, commit and tree hash, LearnLoop's commit and tree hash, and for every path its action, SHA-256 and mode. Removed files are listed by path and SHA-256 only.
- Scripts, documentation, and the evidence files, all written for this repository.

It contains no file from the baseline, no Git history from vision-test-bench or LearnLoop, no assembled application, no credentials, no recordings, no databases, and no stored model responses.

## Residual overlap with pre-kickoff code

New and changed files were written during the hackathon, but some of their lines are textually identical to lines that existed before kickoff. Counting lines longer than 25 characters, after trimming whitespace, that also appear anywhere in the baseline:

| Where | Lines | Identical to a baseline line |
| --- | ---: | ---: |
| New files (`overlay/files/`) | 10,266 | 777 (7.6%) |
| Added lines in edit scripts | 2,944 | 221 (7.5%) |

Most are imports, test fixtures that set up the database the same way, common calls such as `session.get(VideoAsset, video_id)`, and error handling such as `raise HTTPException(404, str(exc)) from exc`. A smaller part is code moved during hackathon refactors from a pre-kickoff module into a new one, for example frame sampling moved from `pipeline/runner.py` into the new `pipeline/sampling_stage.py`. The new files were kept whole, as instructed, rather than broken into references to the baseline.

## Reproducing the overlay

With local clones of both repositories next to this one:

```bash
python3.12 scripts/generate_overlay.py --dependency-repo ../vision-test-bench --reference-repo ../LearnLoop
```

The output is deterministic: running it again produces identical files.

## Tools

Claude Code (Anthropic) was used as a development tool, including to produce this packaging. No Anthropic model runs in the application.

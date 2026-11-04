# LearnLoop — Meta Global AI Developer Hackathon submission

**Teach a physical workflow once. Check a new attempt against what was learned.**

LearnLoop learns a short physical procedure from a recorded demonstration and checks a later recording against it. Meta models propose the procedure and follow each part through the video, a person reviews it, and deterministic code decides each verdict, showing the timestamp and frame behind it.

This repository holds **only work done during the hackathon**. LearnLoop was built on top of a research project the author started before kickoff, [vision-test-bench](https://github.com/ant10293/vision-test-bench). That project is used here as an **external dependency, pinned to its last pre-kickoff commit**, and is never copied into this repository. One script fetches it, applies the hackathon changes stored here, and produces the complete application.

| | |
| --- | --- |
| Hackathon kickoff | 2026-10-26, 12:00 PM ET (16:00 UTC) |
| External dependency | [`ant10293/vision-test-bench`](https://github.com/ant10293/vision-test-bench) at [`27859ac787ae214862488d6348898d012d57353c`](https://github.com/ant10293/vision-test-bench/commit/27859ac787ae214862488d6348898d012d57353c), pushed to GitHub 2026-10-26 07:29 UTC (03:29 AM ET) |
| Product repository during development | [`ant10293/LearnLoop`](https://github.com/ant10293/LearnLoop), assembled result identical to [`8e718ccc49e63bfb5443c77554d98c685818b6e5`](https://github.com/ant10293/LearnLoop/commit/8e718ccc49e63bfb5443c77554d98c685818b6e5) |
| This repository | Created 2026-11-04. No Git history from either repository above |

## Quick start

Requires Git, Python 3.12+, Node.js 20+, and ffmpeg. macOS or Linux.

```bash
scripts/setup.sh
```

```bash
scripts/run.sh
```

Open http://127.0.0.1:5180 (the API is on port 8010).

`setup.sh` assembles the application into `build/LearnLoop/` (Git-ignored), creates `build/LearnLoop/backend/.venv` with the backend and test dependencies plus PyTorch for DINOv2, downloads the DINOv2 weights once, and installs the frontend from its lockfile with `npm ci`. Set `LEARNLOOP_SKIP_PERCEPTION=1` to skip PyTorch (appearance checks then report themselves unavailable), or `LEARNLOOP_E2E=1` to also install the Playwright browser. Running it again rebuilds the application and keeps `.venv`, `node_modules`, `data/` and `.env`.

### Live Meta calls

Live calls are off by default and the app works without a key for browsing and tests. To analyze your own recordings:

```bash
cp build/LearnLoop/.env.example .env
```

Set `MODEL_API_KEY` (Meta Model API) and `LEARNLOOP_LIVE_INFERENCE=1` in `.env`. `scripts/run.sh` copies it into the assembled app. Every live request is also approved in the UI, which shows the model, the number of requests, and the cost if known. `.env` is Git-ignored here and in the app.

### Tests

```bash
scripts/verify.sh
```

This re-runs the byte-for-byte comparison below, the backend tests, the frontend type check and production build, and the frontend tests. Add `LEARNLOOP_E2E=1` to also run the Playwright end-to-end smoke test.

## How this repository is assembled

```
overlay/
  manifest.json        pinned dependency (commit + tree hash), and every path in the result
                       with its action, SHA-256 and file mode
  files/<path>         71 files created during the hackathon, complete
  edits/<path>.edits   66 edit scripts for pre-kickoff files changed during the hackathon
scripts/
  assemble.py          fetch dependency -> apply overlay -> verify -> build/LearnLoop
  setup.sh  run.sh  verify.sh
  compare_with_learnloop.py   independent byte-for-byte check against LearnLoop
  generate_overlay.py         maintainer tool that produced overlay/ from the two commits
docs/
  FILES.md             file-level migration plan: every path and what happened to it
  SUBMISSION_PROVENANCE.md   dates, evidence, and what is and is not in this repository
  DEMO_DISCLOSURE.md   opening disclosure and talking points for the demo video
  evidence/            GitHub server-side push timestamps and repository creation dates
```

`scripts/assemble.py` does this, stopping at the first mismatch:

1. Shallow-fetches vision-test-bench at the pinned commit into `build/deps/` (Git-ignored) and checks both the commit and its tree hash.
2. Exports that commit's files, without Git history, into a staging directory.
3. Deletes the 108 files removed during the hackathon, after checking each one's SHA-256. These were research-only modules LearnLoop does not run: non-Meta providers, the research UI, and the tracking, recovery, evaluation, audio and demo-scenario code.
4. Applies the 66 edit scripts.
5. Copies in the 71 new files.
6. Sets file modes and verifies that all 175 files have the recorded SHA-256 and mode, and that no other file exists.
7. Moves the result into `build/LearnLoop/`.

### Why edit scripts instead of ordinary patches

A normal patch carries context lines and the lines it removes, which are pre-kickoff code. To keep pre-kickoff code out of this repository entirely, each `.edits` file is a `git diff -U0` with the removed lines, context lines and function headers stripped:

```
# LearnLoop hackathon edit script v1
# path: backend/app/config.py
# base-sha256: e63e33e8…
# result-sha256: 99414972…
@@ -26,0 +27,38 @@
+    # Meta bills SAM video per frame. …
```

`@@ -A,B +C,D @@` means "replace B lines of the pinned dependency's file starting at line A with the D lines that follow" (B = 0 inserts after line A). The dependency's lines are referred to by number, never by content, and the SHA-256 of the input and output make the result exact. The format is documented at the top of [`scripts/assemble.py`](scripts/assemble.py).

To read the hackathon changes as a normal diff, run `python3 scripts/compare_with_learnloop.py` (or `scripts/verify.sh`), export the baseline next to the clean assembly it leaves in `build/compare/assembled`, and diff them:

```bash
mkdir -p build/baseline && git -C build/deps/vision-test-bench archive 27859ac787ae214862488d6348898d012d57353c | tar -x -C build/baseline
```

```bash
git diff --no-index --stat build/baseline build/compare/assembled
```

### Byte-for-byte validation

[`scripts/compare_with_learnloop.py`](scripts/compare_with_learnloop.py) does not trust the manifest. It assembles a fresh copy, fetches LearnLoop at `8e718cc` from GitHub, exports it with `git archive`, and compares every path, byte and executable bit, and cross-checks the file list against `git ls-tree`:

```
MATCH: 175 files, 1,728,638 bytes identical to LearnLoop 8e718ccc49e63bfb5443c77554d98c685818b6e5 (tree 9ab0296b9a52a9dea12030f98483df5a04f6ca87)
```

Results on 2026-11-04 (macOS, Python 3.12.2, Node 23.9): byte-for-byte match; Python imports and application startup; Alembic migrations from an empty database to the single head; backend tests 266 passed; `tsc --noEmit` and `vite build` succeeded; frontend tests 51 passed; Playwright smoke test (teach, review, accept, verify, inspect evidence, confirm, export) passed; the home page loaded in a browser with no console errors. A tampered edit script is rejected with `result does not match result-sha256`.

## What existed before kickoff

vision-test-bench, started 2026-10-21, was a research harness for analyzing video with vision models and checking workflows. At the pinned commit it had 212 files. The parts LearnLoop still uses are:

- Database tables and Alembic migrations, video upload, probing and proxies, and run serialization
- The pipeline runner and the Meta API adapter
- The core of the deterministic verifier: role mapping, action alignment, and condition predicates (first committed about nine hours before kickoff)

38 of those files are used unchanged and 66 were changed during the hackathon. Measured line by line, about 4,800 lines of LearnLoop's backend match code from before kickoff. The application's own [PROVENANCE.md](overlay/files/docs/PROVENANCE.md) gives the per-file breakdown.

## What was built during the hackathon

Between kickoff and 2026-11-02 in vision-test-bench (77 commits), and from 2026-11-02 in LearnLoop:

- **Meta-powered procedure learning:** the `hackathon_guided` analysis, with one strict-schema Muse Wonder call per recording, replay keyed by the exact inputs, and approval before any live call (`pipeline/guided.py`, `pipeline/contracts.py`, `api/product.py`)
- **SAM 3.1 tracking:** first-frame object locating with Muse Wonder, SAM 3.1 tracking at 12 frames per second, and re-finding lost objects (`pipeline/object_views.py`, `providers/sam.py` changes, `perception/sam_masks.py`)
- **Appearance-based object matching:** DINOv2 appearance references built from SAM crops, used to tell similar parts apart and as sightings (`perception/appearance.py`, `pipeline/appearance_stage.py`, `services/appearance.py`)
- **New verification capabilities:** the never-seen check, the automatic second look at unresolved steps (`services/reinspection.py`), reviewer observations as audited evidence, reviewer-controlled step ordering, and the verifier changes listed in the application's [ARCHITECTURE.md](overlay/files/docs/ARCHITECTURE.md#changed-during-the-hackathon)
- **A complete user interface:** every page and component in `frontend/src` (Projects, Teach, Procedure, Verify, and the Reliability Lab)
- **Reliability Lab:** repeated isolated runs on one recording to compare results (`reliability/`, `api/reliability.py`)
- Tests for all of the above, and all documentation

[docs/FILES.md](docs/FILES.md) lists every file and what happened to it.

## Meta models

| Purpose | Model | Path |
| --- | --- | --- |
| Procedure analysis of the whole video | `muse-wonder-1.0` | Meta Responses API, native video, strict JSON schema |
| Locating each object on the first frame and on later stills | `muse-wonder-1.0` | Meta Responses API, strict JSON schema |
| Following each object through the recording | SAM 3.1 | Meta Model API |
| Second look at an unresolved step | `muse-wonder-1.0` | Meta Responses API |
| Appearance references | DINOv2 ViT-S/14 (Meta open weights) | Local, frozen weights |

Only Meta models run. The provider registry contains the Meta provider plus local test stubs with no model behind them, and the model catalog is filtered to Meta. The `openai` Python package is used only as the HTTP client for Meta's compatible endpoint (`https://api.meta.ai/v1`).

## Demo

See [docs/DEMO_DISCLOSURE.md](docs/DEMO_DISCLOSURE.md) for the opening disclosure and talking points, and the application's [demo script](overlay/files/docs/DEMO.md) for the step-by-step flow. A live demo needs a `MODEL_API_KEY` and the recordings, which are not in this repository.

## Known limitations

- Results vary between runs on the same recording, and a handful of recordings do not establish accuracy. Relations are coarse, small parts handled close to the hand are often CANNOT VERIFY, and recordings over 60 seconds are not supported.
- Single-user local app with no authentication.
- `scripts/run.sh` uses the application's fixed ports 8010 and 5180, and refuses to start if another process holds them.
- Assembly needs network access to GitHub, or a local clone passed with `VTB_SOURCE=/path/to/vision-test-bench`. It depends on the pinned commit staying available in the public vision-test-bench repository.
- No demo recordings or stored Meta responses are included (`demo/replay/` holds only its README), so cached replay works only after your own approved live calls.
- Tested on macOS. `scripts/dev.sh` in the application uses `lsof`, which most Linux distributions provide. Windows is not supported.

## Links

- Pre-existing research project: https://github.com/ant10293/vision-test-bench (pinned: [`27859ac`](https://github.com/ant10293/vision-test-bench/tree/27859ac787ae214862488d6348898d012d57353c))
- LearnLoop development repository: https://github.com/ant10293/LearnLoop (audited: [`8e718cc`](https://github.com/ant10293/LearnLoop/tree/8e718ccc49e63bfb5443c77554d98c685818b6e5))
- Provenance details: [docs/SUBMISSION_PROVENANCE.md](docs/SUBMISSION_PROVENANCE.md)

Claude Code (Anthropic) was used as a development tool. No Anthropic model runs in the application.

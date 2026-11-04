# Demo disclosure

## Opening, about 15 seconds

Say this first, over a two-column slide:

> "Before the hackathon, I built a research foundation for video processing and workflow verification. During the hackathon, I built LearnLoop on top of it, adding Meta-powered procedure learning, SAM 3.1 tracking, appearance-based object matching, a complete user interface, and new verification capabilities."

| Before kickoff: vision-test-bench, 2026-10-21 to 10-26 | Built during the hackathon |
| --- | --- |
| Database tables and migrations | Muse Wonder guided procedure learning, strict JSON, replay and live-call approval |
| Video upload, probing and proxies | SAM 3.1 object tracking and re-finding lost objects |
| Pipeline runner and Meta API adapter | DINOv2 appearance references for telling similar parts apart |
| Core of the deterministic verifier: role mapping, action alignment, condition predicates | Never-seen check, automatic second look, reviewer observations, step ordering |
| | The whole user interface and the Reliability Lab |

## While showing the product

- Every screen in the video is new: the whole frontend was written during the hackathon.
- At a verdict, say where it comes from: "The verdict engine came from my earlier project. What's new is the evidence it reads, from Muse Wonder, SAM 3.1 and DINOv2, the checks I added to it, and everything you see here."
- A step marked "not seen anywhere" comes from the never-seen check added during the hackathon.
- Do not describe role mapping, action alignment, condition predicates, video ingest or the database as new.

## On the repository

> "The submission repository contains only what I wrote during the hackathon. My earlier project is a pinned external dependency, and one script fetches it, applies my changes, and checks the result byte for byte against the app I built."

## Step-by-step flow

Follow the application's [demo script](../overlay/files/docs/DEMO.md): create a procedure, learn it from a demonstration, review and accept, verify an attempt, inspect the evidence and the second look, confirm a checkpoint, and export.

# Feature backlog

A lightweight idea backlog for omegaUp Community. **This is not a commitment to
implement everything**, and nothing here is designed in detail yet. Items are
captured so they can be prioritized and refined later without losing context.

Relative priority is a rough ordering signal (`high` / `medium` / `low`), not a
schedule. Dependencies reference existing design docs and milestone issues.

See also: product-design §20 (product structure), §21 (omegaUp ideas), §23
(mentor eligibility); technical-design §18 (permission verification), §19 (ideas
sync); `docs/milestone-1.md` (what is explicitly out of scope for M1).

---

## 1. omegaUp GSoC ideas / editions API integration

- **Purpose:** Consume omegaUp's GSoC idea catalog and (potentially) published
  editions, linking them to Community identities, mentors, applications, and
  participants.
- **Value:** Avoids duplicating editorial ownership of idea descriptions; lets
  Community build program workflows on top of omegaUp's authoritative catalog.
- **Dependencies:** A published omegaUp API contract (does not yet exist); the
  job queue/worker (M1-11/M1-12); the Program/Edition model with a
  source/provenance attribute (M1-08 + the note in technical-design §19). Must
  be a reconstructible local projection; omegaUp need not be online per request.
- **Priority:** medium — strategically important, but blocked on an external API
  contract. Keep the data model compatible now; integrate when the API exists.

## 2. Review recommendation engine

- **Purpose:** Recommend pull requests that an experienced contributor or mentor
  is well-suited to review.
- **Value:** Directs scarce reviewer attention; surfaces PRs waiting on review;
  helps mentors spend time on high-value review rather than reconstruction.
- **Dependencies:** GitHub replica of PRs/reviews/labels (product-design §13);
  contributor/reviewer activity signals; the personal dashboard surface
  (product-design §20.1). Benefits from the contribution-correlation work (#8).
- **Priority:** medium — high user value, but depends on a populated GitHub
  replica and good signal quality.

## 3. GitHub activity explorer (incl. recently created issues)

- **Purpose:** Browse recent repository activity — newly created issues, open
  PRs, labels — within Community.
- **Value:** A discovery surface for contributors looking for something to work
  on; feeds "good first issue" and "popular issue" recommendations.
- **Dependencies:** GitHub replica/sync (product-design §13); read models over
  issues/PRs/labels. Public data, so should not require superadmin
  (product-design §20.1).
- **Priority:** medium — foundational for several discovery features.

## 4. Contributor workload view (assigned issues and PRs)

- **Purpose:** Show a contributor's current load: assigned issues, open PRs, and
  review requests.
- **Value:** Helps mentors identify who is ready for more work vs. overloaded vs.
  waiting on review (product-design §14).
- **Dependencies:** GitHub replica of assignments/PRs; the mentor/admin
  surfaces. GitHub remains authoritative for assignment.
- **Priority:** medium.

## 5. PR conversation analysis (high-comment / potentially blocked PRs)

- **Purpose:** Flag PRs that are stalled or contentious — e.g. unusually high
  comment counts, long time-since-last-activity, or review back-and-forth.
- **Value:** Surfaces PRs that need intervention or mentorship before they go
  stale.
- **Dependencies:** GitHub replica including PR comment/review timelines (richer
  than #3/#4); heuristics for "blocked". Rate-limit-aware sync.
- **Priority:** low — valuable but needs richer replica data and tuned
  heuristics.

## 6. Explainable contribution correlations and recommendations

- **Purpose:** Produce recommendations (issues to pick up, reviewers to assign)
  with a human-readable explanation of *why* (e.g. "you've touched these files",
  "you reviewed similar PRs").
- **Value:** Trust and transparency; recommendations users can understand and
  act on; reduces "black box" distrust.
- **Dependencies:** #2, #3, #4; a correlation model over the GitHub replica;
  explanation metadata stored alongside each recommendation.
- **Priority:** low — depends on the discovery/replica features landing first.

## 7. Community health indicators

- **Purpose:** High-signal indicators of community/project health (e.g. review
  latency, stale-PR counts, first-response times, active contributor counts).
- **Value:** Operational insight for maintainers/admins; early warning of
  bottlenecks.
- **Dependencies:** GitHub replica (#3+); clear metric definitions; the
  admin/operational surface (product-design §22, technical-design §13). Keep
  focused — not a giant metrics wall.
- **Priority:** low.

## 8. Contribution-based mentor eligibility

- **Purpose:** Extend mentor eligibility beyond GitHub repository permission to
  include contribution-based criteria (e.g. merged PRs, sustained activity), for
  a future public "become a mentor" invitation.
- **Value:** Broadens the mentor pool fairly and transparently without manual
  vetting of every candidate.
- **Dependencies:** Mentor model (M1-07b); GitHub contribution replica (#3/#4);
  the permission-verification strategy (technical-design §18). Explicitly **out
  of scope for M1-07b** (product-design §23.1).
- **Priority:** low — follows M1-07b and a populated contribution replica.

## 9. Eligible-user mentor request and approval workflow

- **Purpose:** Let a verified-eligible user request mentor status for a scope,
  with a superadmin inbox to approve or reject (`pending → approved | rejected`),
  rather than superadmins assigning every mentor directly.
- **Value:** Scales mentor onboarding beyond manual assignment; gives candidates
  a self-service path once they are known to be eligible.
- **Dependencies:** Reliable GitHub repository-permission verification
  (technical-design §18) is a hard prerequisite — the request action must only
  be offered to eligible users (product-design §23.1). Builds on the direct
  assignment model from M1-07b (mentor assignments, audit history, scoping).
- **Priority:** medium — the natural successor to M1-07b, blocked on permission
  verification. Split out of the originally-planned M1-07b scope.

---

## Notes

- Items 2–7 share a common prerequisite: a populated, reconstructible GitHub
  replica (product-design §13) driven by the job queue/worker. Sequencing that
  replica unlocks most of this backlog.
- Nothing here changes an existing architectural decision. Where an item touches
  identity, roles, sync, or evaluation visibility, the existing guardrails
  (AGENTS.md, technical-design §17) still apply — notably: no synchronous
  external sync in request paths, and internal evaluations/rankings are never
  exposed to contributors.

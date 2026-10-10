# Contributor Community Platform — Product Design v1

## 1. Purpose

Build a standalone platform for managing and supporting omegaUp contributors across programs such as Google Summer of Code (GSoC), internships, school residencies, and volunteer initiatives.

The platform complements GitHub and omegaUp; it does not replace either. GitHub remains the source of truth for contribution work. omegaUp remains the source of truth for contest/test activity. The platform provides identity linking, program workflows, progress visibility, mentor operations, document review, and internal evaluation.

The initial deployment is independent from the main omegaUp application, with the long-term goal of proposing it as `community.omegaup.com` and transferring its repository to the omegaUp organization.

## 2. Product principles

- GitHub is the source of truth for issues, pull requests, reviews, labels, milestones, and contribution state.
- The local GitHub dataset is a partial, reconstructible replica.
- A pull request counts as completed only when it is merged; there are no intermediate completion interpretations.
- omegaUp is the source of truth for test/contest results.
- Contributors should understand their own progress without needing mentor-only information.
- Internal evaluations and rankings are never exposed to contributors.
- Mentors should spend their time reviewing exceptions and qualitative work rather than manually reconstructing activity.
- Program rules should be configurable per edition rather than hardcoded for GSoC.
- Administrative workflows should not require infrastructure changes or deployments when ordinary product configuration is sufficient.

## 3. Core concepts

### Person and identities

A person represents a contributor, mentor, or administrator. A person may have multiple external identities:

- GitHub — primary authentication identity.
- omegaUp — linked and verified for test/progress tracking.
- Discord — informational identity used to recognize contributors in community discussions.

Identity relationships are many-to-one with Person and should tolerate username changes while preserving history where useful.

### Program

A reusable category of activity, such as:

- GSoC
- Internship
- School residency
- Volunteer program

### Edition

A concrete occurrence of a program, e.g. `GSoC 2027` or `ITSUR Residency 2027`.

An edition owns configuration, dates, repositories, phases/requirements, announcements, applications, and relevant projects.

An edition can be created from another edition by an administrator to reuse configuration.

### Application / participation

Connects a person with an edition. Access may originate through:

- open enrollment/link,
- invitation,
- administrator enrollment.

GSoC historically allows broad participation; other programs may use invitations or admin enrollment.

### Project

Represents a project within an edition. Interns/residents normally work on a project. GSoC candidates may submit documents/proposals for multiple projects.

A person may relate to multiple projects and projects may have multiple people.

### Phases and requirements

Editions define ordered phases containing requirements. Rules are configurable per edition.

Examples:

- omegaUp test
- development-environment video
- GitHub contributions
- proposal/design document

A requirement may be automatic, manual, or automatic with manual approval.

Suggested progress states:

- `PENDING`
- `IN_PROGRESS`
- `SATISFIED`
- `APPROVED`

A phase is complete when its required requirements are approved.

## 4. Contributor onboarding

The primary entry point is GitHub authentication.

A typical GSoC flow:

1. Contributor follows a link from the pinned Discord instructions.
2. Contributor signs in with GitHub.
3. The platform creates or finds their Person/GitHub identity.
4. The platform asks for optional-but-important profile connections:
   - omegaUp account
   - Discord username
5. Skipping these fields does not block dashboard access.
6. The contributor immediately sees any GitHub history already known for their account.

The UI explains that linking omegaUp is required for automatic test progress tracking and that Discord helps mentors recognize them in community discussions.

## 5. omegaUp identity linking

omegaUp API tokens can be used to prove account ownership.

Flow:

1. Contributor enters an omegaUp API token.
2. Backend calls omegaUp's authenticated current-session API.
3. Backend obtains the actual omegaUp username associated with the token.
4. The Person ↔ omegaUp identity association is stored with verification metadata.
5. The contributor's personal API token is discarded and must not be persisted or logged.

The program's scoreboard credential is separate from the contributor's personal token.

## 6. GSoC workflow

GSoC is the most sophisticated initial program and drives the generic workflow engine.

### Test phase

Per-edition configuration includes at least:

- contest alias
- scoreboard URL
- number of distinct correctly solved problems required
- whether mentor approval is required after automatic satisfaction

The platform consumes omegaUp scoreboard and scoreboard events.

`scoreboardEvents` provides the submission-by-submission timeline, allowing the platform to determine the exact timestamp when the Nth distinct problem received an AC. Duplicate ACs for the same problem do not increase the solved-problem count.

The historical completion timestamp (e.g. second AC) remains available for ordering/visualization, but it is not the sole basis for assignment decisions.

Manual approval is supported so mentors can resolve anomalies/questions before formally advancing a contributor.

### Development-environment video

Candidates may provide a link to a video showing them making a contribution.

Goals include observing:

- development environment setup,
- whether official documentation works in practice,
- alternate useful setup steps,
- recurring setup bugs,
- opportunities to improve the project wiki/documentation.

Mentors review and approve the requirement. The platform stores the link and review/progress metadata, not the video itself.

### Contributions

Contribution requirements are configurable, including:

- minimum merged contributions,
- required GitHub label (e.g. `GSoC`).

Only merged pull requests count as completed contributions.

Candidates who have completed the test and video phases receive priority for issue assignment / PR review. GitHub remains authoritative for assignment and PR state; the dashboard only provides guidance/visibility.

### Documents

The generic concept is a **document submission**, not only a proposal.

Examples:

- GSoC proposal
- internship design document

Documents may be stored as external links. An edition can configure how many submissions are accepted for review (for example, maximum proposal count).

Contributors can request **document review**. This does not mean requesting GitHub PR review.

Document review is manual and may occur in multiple rounds. For GSoC, mentors normally focus review effort on candidates who completed prerequisite phases.

## 7. Contributor dashboard

A contributor sees only information relevant to their own participation, including:

- general announcements,
- current edition/program,
- phase and requirement progress,
- omegaUp test progress,
- video-review progress,
- contribution progress,
- document/proposal links,
- document review requests/status,
- relevant GitHub activity,
- project progress for internships/residencies.

Internal mentor evaluation and ranking results are explicitly excluded.

## 8. Internship / residency experience

Interns and school residents normally participate through a project.

Their dashboard should focus on project progress. GitHub remains the source of truth; the platform may present a consolidated view of:

- linked repository/repositories,
- milestone(s),
- issues,
- pull requests,
- project progress.

GitHub milestones may be used where useful but are not mandatory platform concepts.

## 9. Announcements

Editions support simple announcements visible to relevant participants. The first version does not require a complex messaging or notification system.

## 10. Community recognition

Mentors may grant positive recognition (conceptually `+1`) for contributions beyond assigned implementation work, such as:

- helping others in GitHub issues,
- useful PR reviews,
- helping contributors in Discord discussions.

Recognition is stored historically with actor, recipient, reason/context, timestamp, and optional edition association.

Recognition can inform later evaluation but does not automatically determine outcomes.

## 11. Mentors and administration

During the open selection process, mentors generally operate as a shared pool: all mentors may assist all candidates.

After GSoC selection, primary/secondary mentor assignments may be recorded for selected contributors/projects.

Administrators have platform-level responsibilities such as creating/cloning editions and managing system configuration. Mentor roles may be edition-scoped and transient.

## 12. Internal evaluation and ranking

After candidates complete the required selection phases, mentors perform an internal evaluation.

This is intentionally separate from contributor-visible progress.

### Evaluations

Each mentor records their own evaluation. Scores must not be naïvely averaged across mentors because evaluators may use scales differently. For example, one mentor's `6` may represent work another mentor would score `9`.

The data model must preserve individual evaluator scores and support normalization/comparison without penalizing a candidate merely because a stricter evaluator reviewed them.

### Project-sensitive ranking

Ranking is not simply global candidate ranking.

A strong candidate may have:

- a weaker proposal in a highly competitive project,
- another proposal for a less competitive project where the candidate should rank much higher.

Therefore ranking must support candidate/application/document × project context.

Mentors rank candidates flexibly per relevant project/proposal. The system may use phase scores, recognitions, document reviews, contribution history, and mentor evaluations as decision support, but the final internal ranking remains a human decision.

The system does not expose final selection/evaluation results to candidates as part of V1.

## 13. GitHub integration product behavior

The platform can synchronize administrator-selected repositories. Initially this is `omegaup/omegaup`.

The local replica may include the details required for product workflows, such as:

- contributors/users,
- issues,
- pull requests,
- labels,
- reviews,
- milestones,
- relationships/status needed for workload and progress views.

It is not intended to be a permanent full GitHub archive. It must be reconstructible from GitHub.

Administrators can review available synchronization targets/data and choose what should be synchronized.

## 14. Workload and assignment support

Outside strict GSoC rules, GitHub activity is used to show contributor workload and progress rather than to replace GitHub project management.

The dashboard may help mentors identify:

- contributors ready for additional work,
- contributors already carrying multiple issues/PRs,
- contributors waiting for review,
- high-priority candidates who completed prerequisite phases.

GitHub remains authoritative for actual assignment.

## 15. Deadlines and exceptions

Editions/phases may define deadlines. Late entrants are supported according to edition policy rather than silently excluded.

Mentors/admins may grant explicit exceptions/extensions where appropriate. Manual approvals and overrides are audited.

## 16. Auditability

Important human decisions should preserve history, including:

- manual phase/requirement approvals,
- overrides and deadline exceptions,
- document reviews,
- recognitions,
- evaluations,
- rankings,
- significant edition configuration changes.

Operational logs are separate from product audit history.

## 17. Roles and visibility

### Contributor

Can access their own profile, participation, progress, documents, review requests, announcements, and relevant project/GitHub information.

### Mentor

Can access edition participants, review queues, progress, manual approvals, document reviews, recognitions, and internal evaluation/ranking features where authorized.

### Administrator

Can manage programs/editions, configuration, integrations/synchronization, administrative enrollment/access, and platform-level operations.

Frontend route guards are only UX. Backend authorization is authoritative.

## 18. Explicit non-goals for V1

- Replacing GitHub issue/PR assignment or review workflows.
- Mirroring all of GitHub permanently.
- Mirroring omegaUp's complete database.
- Storing contributor videos.
- Hosting proposal/design-document content when links are sufficient.
- Publishing internal mentor evaluation or ranking results to candidates.
- Building a general chat/Discord replacement.
- Encoding GSoC-only concepts so deeply that internships/residencies cannot reuse the platform.

## 19. Initial deployment roadmap

1. Build and run V1 on the project owner's VPS.
2. Optionally migrate PostgreSQL to Neon Free when useful rather than as a prerequisite.
3. Demonstrate the functioning WebApp to omegaUp leadership and propose `community.omegaup.com`.
4. If approved, evaluate/apply to the Neon Open Source Program in parallel with production planning.
5. Transfer the repository/infrastructure ownership to omegaUp and deploy under the agreed omegaUp environment.

The application should remain portable PostgreSQL software rather than depending on provider-specific database features.

## 20. Product structure: three complementary areas

This section consolidates how the product is organized. It is a structural
clarification of concepts already described in §7 (contributor dashboard), §8
(internship/residency experience), §11 (mentors and administration), and §17
(roles and visibility). It does not replace those sections or expand Milestone 1.

The platform presents three complementary areas, each with a distinct audience
and purpose:

### 20.1 Personal dashboard / Contributions

The signed-in user's own, personalized space.

- Personalized to the user's own activity and responsibilities.
- Surfaces the user's GitHub contributions, relevant issues, pull requests, and
  opportunities to contribute.
- Experienced contributors and mentors may additionally receive review
  recommendations here.
- Focused on actionable recommendations and the user's own contributions, not
  on administrative metrics.
- Repository activity and contribution insights that are derived from
  **public** information must not require platform superadmin privileges. Any
  authenticated user may see public repository/contribution insights relevant
  to them; internal mentor-only data (evaluations, rankings) remains gated per
  §12 and §17.

### 20.2 Programs

The structured program workflows (see §3 Core concepts).

- Programs include GSoC, internships, residencies, and volunteer programs.
- A Program has Editions; an Edition may contain Projects.
- Mentors, participants, applications, requirements, reviews, and evaluations
  are associated at the appropriate Program / Edition / Project scope — never
  globally.
- Program rules remain configurable per edition rather than hardcoded for GSoC
  (§2).

### 20.3 Administration

The superadmin/operator space (see §11, §17, and §22).

- Program and edition management (create/clone/configure).
- Mentor approvals and assignments.
- Access control, integration configuration, synchronization, and operational
  oversight.
- The superadmin administration dashboard is a **separate** surface from the
  user's personal dashboard (§20.1). The two must not be conflated: a user may
  be both a contributor and a superadmin, but the personal and administration
  experiences are distinct entry points.

These areas share the same identity and authorization foundations (Person,
ExternalIdentity, platform roles, mentor scoping) but are presented as separate
navigational contexts.

## 21. omegaUp GSoC ideas integration (future direction)

omegaUp has in-progress work on a GSoC ideas organizer. This section records the
intended direction so later models stay compatible. It is **not** a commitment
to a specific API contract, and **no integration is implemented yet**. The API
contract must not be assumed to exist.

### 21.1 Ownership and authority

- omegaUp remains the authoritative source for the GSoC **idea catalog**, and
  potentially for published editions and active-edition information.
- A future omegaUp API may expose editions and their ideas; Community will
  consume that information.
- Community does **not** take editorial ownership of idea descriptions. It links
  omegaUp-sourced ideas/editions to real Community identities, mentors,
  applications, and participants.

### 21.2 Idea vs. project

- An **idea** is an editorial catalog entry owned by omegaUp (a proposal topic a
  candidate might pursue).
- A **project** (§3) is a unit of work being executed within a Community
  Edition, associated with people and GitHub repositories.
- These are distinct concepts. An idea may inspire or map to a project, but a
  project is not merely a copy of an idea, and the two have different owners and
  lifecycles.

### 21.3 Synchronization and persistence

- Consistent with the GitHub replica policy (§13, technical-design §7), the
  omegaUp ideas/editions data is a **locally persisted, reconstructible
  synchronization projection**. Page/API requests read local state; they do not
  require the omegaUp API to be online.
- Preserve stable external identifiers (omegaUp idea/edition ids) and edition
  associations so the projection can be reconstructed and re-linked.
- Clearly distinguish **omegaUp-owned fields** (idea title/description, edition
  publication state) from **Community-owned fields** (mentor links,
  applications, participant associations, internal review/evaluation state).

### 21.4 Interaction with existing Program / Edition / Project models

This direction interacts with the Program/Edition/Project models (M1-08) and
needs an explicit modeling decision later (tracked as an open decision):

- **Not all Community editions originate in omegaUp.** Internships, residencies,
  and volunteer programs may be created and managed directly in Community.
- Editions therefore need a notion of **provenance/source** — e.g. a
  Community-managed edition vs. an edition projected from omegaUp — plus an
  optional stable external identifier when the source is omegaUp.
- The Program/Edition/Project schema must not assume an omegaUp origin, and must
  not require omegaUp connectivity to create or manage a Community-native
  edition.

## 22. Admin (superadmin) dashboard concept

A proposed superadmin landing page (the Administration area, §20.3), kept
deliberately focused rather than a catch-all metrics wall.

It should prioritize, in roughly this order:

1. **Active editions and programs** — what is currently running.
2. **Pending administrative actions** — things awaiting a decision.
3. **Mentor assignments** — current project-scoped mentors, with direct
   assign/revoke (see §23). A mentor request/approval review queue is a future
   addition gated on eligibility verification (§23.1).
4. **Relevant participant and program summaries** — high-signal counts, not
   exhaustive metrics.
5. **Integration / synchronization status** — GitHub and (future) omegaUp sync
   freshness and recent failures (distinct from infrastructure health, see
   technical-design §13).
6. **Navigation to detailed management pages** — the dashboard orients and
   routes; deep management lives on dedicated pages.

Explicitly avoid a single giant dashboard that renders every available metric.
The personal dashboard (§20.1) is the counterpart surface and instead focuses on
actionable recommendations and the user's own contributions.

## 23. Mentor eligibility and management

This section refines the mentor model in §11. It does not change the
contributor-visibility rules (§12, §17).

### 23.1 Mentorship is not open self-service

GSoC mentorship is not available to all users as a self-service action. A
"request mentor" action, if offered at all, must only be **offered** to users
who are verified as having sufficient permissions on `omegaup/omegaup`.

- A provisional eligibility threshold is **GitHub `Triage` permission or higher**
  on `omegaup/omegaup`. This threshold is subject to product confirmation.
- GitHub permission eligibility is **necessary but not sufficient**: it gates who
  may request/be offered mentorship, but it never automatically grants mentor
  status.
- A future public "become a mentor" invitation may add contribution-based
  criteria; those criteria are out of scope.

Because reliable GitHub repository-permission verification is deferred
(§23.4, technical-design §18), the **self-service mentor request workflow is not
built in the initial milestone work**. The first mentor capability (milestone
issue M1-07b) is **direct assignment by superadmins only** (§23.2). The
eligible-user request/approval workflow is tracked in `docs/feature-backlog.md`
and depends on reliable permission verification.

### 23.2 Assignment and approval

- Superadmins **directly assign and revoke** mentors. This is the initial
  mechanism (M1-07b).
- A request/approval lifecycle (users request; superadmins approve or reject) is
  a **future** addition gated on eligibility verification (see §23.1 and the
  feature backlog); it is not part of the initial direct-assignment work.
- Mentor permissions are scoped to the relevant **program / edition / project**,
  never global platform administration (§11, §17).
- Assignments, revocations, and any future approvals/rejections are recorded
  with an **auditable history** (actor, action, timestamp, optional note)
  consistent with §16.

### 23.3 Pool mentors vs. assigned mentors

Preserve the distinction already noted in §11:

- **Shared-pool mentors** assist the whole GSoC candidate pool during the open
  selection process.
- **Primary/secondary mentors** are assigned to selected projects or
  contributors after selection.

The mentor model must represent both without conflating them.

### 23.4 GitHub permission verification (least-privilege, not yet implemented)

Establishing effective repository permissions is a prerequisite for §23.1 and is
**not implemented**. Current OAuth scopes (`read:user`) do not expose repository
permission data, so a verification strategy must be designed deliberately. See
technical-design §18 for the proposed least-privilege options and open
questions. Do not assume existing scopes suffice.

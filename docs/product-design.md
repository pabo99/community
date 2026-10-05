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

# kansei

A job board for engineers in Japan, filled from companies' Greenhouse, Lever, Ashby and HRMOS boards.

## Language

**Board**:
One company's job board on Greenhouse, Lever, Ashby or HRMOS, named by its source and token, such as `greenhouse:stripe` or `hrmos:visional`. A company can have more than one. Users add and follow boards, though the pages call them companies.
_Avoid_: Company, source

**Candidate**:
A posting whose title is an engineering role and whose location is in Japan or remote without naming another place. An HRMOS posting that names no location counts as in Japan, and its headline on the board page counts as a title too.
_Avoid_: Match, Japan posting

**Company name**:
The name a board's company goes by, such as `Woven by Toyota` for `lever:woven-by-toyota` or `ビジョナル株式会社` for `hrmos:visional`. A board may have none. A pasted posting has no board, so it goes by the `hiringOrganization` name its page declares. A posting with neither goes by its token.
_Avoid_: Employer, organization

**Listed**:
Said of a posting kansei saw within the last two days. The postings page shows only listed candidates. A tracked posting that isn't listed shows as no longer listed, whether its board took it down or it stopped being a candidate, since kansei can't tell the two apart.
_Avoid_: Closed, expired

**Follow**:
A user's choice to see one board's candidates on their own page.
_Avoid_: Subscription, watch, favorite

**Tracked posting**:
A posting a user keeps in their tracker, with its stage and a note. Untracking deletes it.
_Avoid_: Application, saved job, job, bookmark

**Stage**:
How far a user has got with a tracked posting: saved, applied, interviewing or offer. Archiving doesn't change it.
_Avoid_: Status, step, phase

**Archived**:
Said of a tracked posting the user is no longer pursuing, for any reason: the company turned them down, they withdrew, the company never replied, or they lost interest. It keeps its stage.
_Avoid_: Rejected, closed, inactive

**Moved**:
The last time a user changed a tracked posting's stage, or archived or unarchived it. Editing the note doesn't move it.
_Avoid_: Updated, last activity, stage changed

**Extraction**:
The facts the model read out of one posting's text, stored with that exact text, the model and the prompt.
_Avoid_: Summary, parse

**Pending extraction**:
A candidate with no extraction for its current text under the current model and prompt. `LLM_MAX_POSTINGS` caps how many are sent per run, and `LLM_DAILY_LIMIT` caps how many extractions are created in any 24 hours.
_Avoid_: Uncached, new or changed, stale

**New**:
Said of a candidate first seen within the last two days. It is the same for every user.
_Avoid_: Fresh, recent, unseen

**Japanese requirement**:
How much Japanese a candidate asks for: basic, conversational, business or native; none, when Japanese is only preferred or not required; or not stated, when the posting says nothing about it. A JLPT level stands in when no level is named: N1 and N2 are business, N3 conversational, N4 and N5 basic. Japanese that is required with no level is business.
_Avoid_: Japanese level, language requirement

**Specialty**:
A kind of engineering a candidate is for: backend, frontend, fullstack, mobile, infrastructure, data, ML, security, QA, embedded, management or customer-facing. A candidate can have several. One whose work isn't on this list, including one that isn't engineering, has no listed specialty and counts as other. They come from the title first. When the title names no area of work, only management or customer-facing or nothing at all, the duties add the areas. A fullstack candidate is also frontend and backend.
_Avoid_: Category, job function, role type, discipline

**Checked**:
The last time kansei saw a posting on any board. A pasted posting doesn't move it, so it says when the boards were last read, whether or not anything on them changed.
_Avoid_: Updated, last run, refreshed, synced

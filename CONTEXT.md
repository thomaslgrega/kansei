# kansei

A job board for engineers in Japan, filled from companies' Greenhouse, Lever and Ashby boards.

## Language

**Board**:
One company's job board on Greenhouse, Lever or Ashby, named by its source and token, such as `greenhouse:stripe`. A company can have more than one. Users add and follow boards, though the pages call them companies.
_Avoid_: Company, source

**Candidate**:
A posting whose title is an engineering role and whose location is in Japan or remote without naming another place.
_Avoid_: Match, Japan posting

**Company name**:
The name a board's company goes by, such as `Woven by Toyota` for `lever:woven-by-toyota`. A board may have none. A pasted posting has no board, so it goes by the `hiringOrganization` name its page declares. A posting with neither goes by its token.
_Avoid_: Employer, organization

**Follow**:
A user's choice to see one board's candidates on their own page.
_Avoid_: Subscription, watch, favorite

**Extraction**:
The facts the model read out of one posting's text, stored with that exact text, the model and the prompt.
_Avoid_: Summary, parse

**Pending extraction**:
A candidate with no extraction for its current text under the current model and prompt. `LLM_MAX_POSTINGS` caps how many are sent per run.
_Avoid_: Uncached, new or changed, stale

**New**:
Said of a posting first seen within the last two days. It is the same for every user.
_Avoid_: Fresh, recent, unseen

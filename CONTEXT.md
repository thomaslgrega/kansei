# kansei

A job board for engineers in Japan, filled from companies' Greenhouse and Lever boards.

## Language

**Board**:
One company's job board on Greenhouse or Lever, named by its source and token, such as `greenhouse:stripe`. A company can have more than one.
_Avoid_: Company, source

**Candidate**:
A posting whose title is an engineering role and whose location is in Japan or remote without naming another place.
_Avoid_: Match, Japan posting

**Company name**:
The name a board's company goes by, such as `Woven by Toyota` for `lever:woven-by-toyota`. A board may have none, and a pasted posting has no board, so such a posting goes by its token instead.
_Avoid_: Employer, organization

**Extraction**:
The facts the model read out of one posting's text, stored with that exact text, the model and the prompt.
_Avoid_: Summary, parse

**Pending extraction**:
A candidate with no extraction for its current text under the current model and prompt. `LLM_MAX_POSTINGS` caps how many are sent per run.
_Avoid_: Uncached, new or changed, stale

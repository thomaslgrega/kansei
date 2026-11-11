# Archived is a flag on a tracked posting, not a stage

A tracked posting has a **Stage** (saved, applied, interviewing, offer) and, separately, may be **Archived**. Archiving keeps the stage, so the tracker can show how far the user got, and picking a stage again unarchives the posting where it left off.

Making archived a fifth stage, as the old `rejected` status was, would be one column instead of two, but archiving would erase the stage. A posting archived after three interviews would look like one saved and forgotten, and unarchiving would have to guess a stage. Users leave a process from any step, not only after an offer, so the stage they reached is the fact worth keeping.

Old `rejected` rows had no recorded stage. They became archived at applied, since a rejection implies an application.

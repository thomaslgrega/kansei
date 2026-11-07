# Users add and follow boards, not companies

Users add a company by finding one of its boards (Greenhouse, Lever or Ashby) and confirming it from sample job titles. What they add and follow is that **Board**. kansei has no Company entity. The pages say "company" and show the board's company name.

A company with two boards, such as an old Lever board and a new Ashby one, takes two follows. Such companies are rare on these ATSs. A Company entity that owns boards would need a new table, a backfill of the existing boards, and a rule for who merges two boards into one company. Following the company name instead would break whenever two boards report different names.

If multi-board companies turn out to matter, a Company can be added later that groups boards. Existing follows of boards can then map to their board's company.

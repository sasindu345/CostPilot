# 0008: Read bills with Python's csv module and Decimal

**Status:** Accepted, 2 Nov 2026

**Situation.** The brief says Pandas should process uploaded bills. Pandas normally turns numbers into binary decimals, which causes small rounding errors, and loads whole files into memory.

**Decision.** Read bills row by row with Python's `csv` module and exact `Decimal` values. PostgreSQL adds up the totals. Pandas and NumPy stay in the plan for Phase 4, for finding unusual spending.

**Why.** Totals stay exact, and a large bill uses little memory, which matters on a 2 GB server.

**Trade-offs.** Reading row by row is slower than Pandas for very large files. That is acceptable, as it runs in the background.

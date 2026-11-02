# 0001: Use FOCUS as the common bill format

**Status:** Accepted, 2 Nov 2026

**Situation.** The brief started with AWS only, but CostPilot must also support Azure, Google Cloud, Oracle and DigitalOcean. Each has its own bill format.

**Decision.** Convert every bill into FOCUS, an open standard for cloud bills. Our main table uses FOCUS column names.

**Why.** AWS, Azure, Google Cloud and Oracle are all listed as FOCUS data generators, so one reader can cover much of the work. New clouds only add a reader.

**Trade-offs.** A summary file like Cost Explorer has no line items, so we store a `detail_level` for each record. DigitalOcean has no FOCUS export and needs its own reader. Each provider's real export must be tested, as support differs.

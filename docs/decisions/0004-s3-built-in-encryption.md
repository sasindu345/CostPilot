# 0004: Use S3's built-in encryption

**Status:** Accepted, 2 Nov 2026

**Situation.** The brief suggested custom AES-256-GCM encryption with AWS KMS for bill files.

**Decision.** Use S3's built-in AES-256 encryption. KMS can be turned on later with a setting.

**Why.** It is free and needs no encryption code from us. Hand-written encryption is easy to get subtly wrong. A customer KMS key costs $1 a month.

**Trade-offs.** With S3's own keys, access is controlled only by S3 permissions, not by a separate key policy. That is acceptable for now, and KMS is the upgrade path.

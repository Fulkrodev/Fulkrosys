"""FULKRO Self-Monitoring System (atom 9.bis.6).

Autonomous verification of FULKRO's own compliance posture across:

- RGPD (UE 2016/679) — endpoint health, RoPA freshness, cookie consent renewal
- LOPDGDD (3/2018) — DPO contact channel, AEPD notification readiness
- LSSI-CE (34/2002) — legal pages reachability
- NIS2 (UE 2022/2555) — security.txt, vulnerability inbox, supply chain DPA expirations
- ISO 27001:2022 — backups integrity, audit log continuity, RLS coverage,
  SSL cert expiry, ISMS doc review cadence

Checks run on a Celery beat cadence (daily/weekly/monthly/quarterly).
Each non-green transition produces a ``ComplianceAlert``; HIGH severity
triggers an immediate email to Marcos, MEDIUM/LOW are batched into the
daily/weekly digest.

The whole subsystem is platform-global (no project_id, no RLS) and
admin-only.
"""

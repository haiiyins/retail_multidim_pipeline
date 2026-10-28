### Candidate recall@200 overall and per source (R1 repurchase, R2 co-purchase, R3 web, R4 sport × offer, R5 best-sellers)

| country code | split | delta | positives | recall any | recall r1 | recall r2 | recall r3 | recall r4 | recall r5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| VN | train | 30 | 61,915 | 0.381 | 0.0815 | 0.0869 | 0.0001 | 0.0002 | 0.3173 |
| VN | train | 90 | 184,082 | 0.355 | 0.0735 | 0.0757 | 0.0001 | 0.0002 | 0.2976 |
| VN | valid | 30 | 18,670 | 0.3632 | 0.0853 | 0.0673 | 0 | 0.0006 | 0.3094 |
| VN | valid | 90 | 51,882 | 0.3456 | 0.0806 | 0.0606 | 0 | 0.0003 | 0.2951 |
| VN | test | 30 | 62,870 | 0.3497 | 0.0735 | 0.0408 | 0 | 0.0001 | 0.3079 |
| VN | test | 90 | 188,228 | 0.3239 | 0.0649 | 0.0348 | 0 | 0.0001 | 0.286 |

*Source:* `audit.candidate_recall` (`models/audit/candidate_recall.sql`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.

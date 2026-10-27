"""Self-built source #1a — public holidays per country (holidays library) → ext.public_holidays.
Inferred commercial events live in the dbt model silver/slv_calendar_enriched.sql.
Country codes come from COUNTRIES in .env (SG, TH, VN; scope decision 2026-10-28, issue #54)."""
import holidays, duckdb, pandas as pd, os
from dotenv import load_dotenv
load_dotenv()
COUNTRIES = os.environ.get("COUNTRIES", "SG,TH,VN").split(",")
SUBDIV = {"AU": ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]}  # none of SG/TH/VN needs subdivisions; kept as an example
rows = []
for c in COUNTRIES:
    c = c.strip()
    if c == "XX":
        continue
    for sd in (SUBDIV.get(c) or [None]):
        try:
            h = holidays.country_holidays(c, subdiv=sd, years=range(2023, 2027))
        except Exception:
            h = holidays.country_holidays(c, years=range(2023, 2027))
        rows += [(c, sd, d, n) for d, n in h.items()]
df = pd.DataFrame(rows, columns=["country_code", "subdivision", "holiday_date", "holiday_name"])
con = duckdb.connect(os.environ["DUCKDB_PATH"])
con.execute("CREATE SCHEMA IF NOT EXISTS ext")
con.execute("CREATE OR REPLACE TABLE ext.public_holidays AS SELECT * FROM df")
# Commercial-event names: a small dictionary (country, window, name) maintained by the team after looking at the peaks the
# dbt model infers from the promotion share (ingestion/commercial_event_names.csv). Windows are matched by overlap in
# slv_calendar_enriched; peaks without a name stay EVENT_n.
names = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commercial_event_names.csv")
con.execute(f"""CREATE OR REPLACE TABLE ext.commercial_event_names AS
  SELECT country_code, CAST(event_start AS DATE) AS event_start, CAST(event_end AS DATE) AS event_end, event_name
  FROM read_csv('{names}', header=true, columns={{'country_code':'VARCHAR','event_start':'DATE','event_end':'DATE','event_name':'VARCHAR'}})""")
n_names = con.execute("SELECT COUNT(*) FROM ext.commercial_event_names").fetchone()[0]
print(f"{len(df)} holidays for {sorted(set(df.country_code))}; {n_names} named commercial-event windows")

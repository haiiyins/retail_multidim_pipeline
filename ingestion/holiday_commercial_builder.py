"""Self-built source #1a — public holidays per country (holidays library) → ext.public_holidays.
Inferred commercial events live in the dbt model silver/slv_calendar_enriched.sql.
TODO: set the 5 country codes (COUNTRIES in .env) after step 2 (see data/audit/csv_profile.md)."""
import holidays, duckdb, pandas as pd, os
from dotenv import load_dotenv
load_dotenv()
COUNTRIES = os.environ.get("COUNTRIES", "XX,XX,XX,XX,XX").split(",")   # TODO
SUBDIV = {"AU": ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]}  # add MY/IN/NZ subdivisions if among the 5 countries
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
con.execute("""CREATE TABLE IF NOT EXISTS ext.commercial_event_names(
  country_code VARCHAR, event_start DATE, event_end DATE, event_name VARCHAR)""")   # named manually after inference
print(f"{len(df)} holidays for {sorted(set(df.country_code))}")

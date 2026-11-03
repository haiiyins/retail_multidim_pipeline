import json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from check_public import check_showcase

ITEM = {"model_id": "M0123456789", "department": "Dept 03", "price_band": 2, "repeat": False, "bought": True}
MEMBER = {"member_id": "TH-001", "country_code": "TH", "segment": "new", "history": [], "bought": [], "best": [ITEM],
          "status_quo": [ITEM]}


def test_showcase_accepts_the_published_fields():
    assert check_showcase({"members": [MEMBER]}) == []


def test_showcase_rejects_raw_ids_and_extra_fields():
    bad = {**MEMBER, "member_id": "123456", "email": "x", "best": [{**ITEM, "model_id": "8524731", "price": 9.9}]}
    hits = check_showcase({"members": [bad]})
    assert any("member fields" in h for h in hits) and any("member_id" in h for h in hits)
    assert any("model_id '8524731'" in h for h in hits) and any("price" in h for h in hits)


def test_cli_flags_uuid_and_unhashed_csv(tmp_path):
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "models_TH.csv").write_text("model_id,department\nM0123456789,Dept 01\n8524731,Dept 02\n")
    (tmp_path / "about.md").write_text("member 0f8fad5b-d9cb-469f-a165-70867728950e\n")
    env = {k: v for k, v in os.environ.items() if k != "REDACT_TERMS"}
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_public.py"), "--dir", str(tmp_path)], capture_output=True,
                       text=True, env=env)
    assert r.returncode == 1 and "UUID" in r.stdout and "not a salted hash" in r.stdout
    (tmp_path / "about.md").write_text("ok\n")
    (tmp_path / "reference" / "models_TH.csv").write_text("model_id,department\nM0123456789,Dept 01\n")
    (tmp_path / "reference" / "showcase.json").write_text(json.dumps({"members": [MEMBER]}))
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_public.py"), "--dir", str(tmp_path)], capture_output=True,
                       text=True, env=env)
    assert r.returncode == 0, r.stdout

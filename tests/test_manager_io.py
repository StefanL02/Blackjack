import csv
from blackjack import GameManager, Rules

def test_get_next_run_id_returns_1_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    assert gm.run_id == 1


def test_get_next_run_id_returns_1_when_file_has_only_header(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with open("summary_stats.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Run ID", "rounds"])
        writer.writeheader()

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    assert gm.run_id == 1


def test_get_next_run_id_returns_last_plus_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with open("summary_stats.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Run ID", "rounds"])
        writer.writeheader()
        writer.writerow({"Run ID": 1, "rounds": 10})
        writer.writerow({"Run ID": 2, "rounds": 20})

    gm = GameManager(6, 1, rules=Rules, verbose=False)

    assert gm.run_id == 3








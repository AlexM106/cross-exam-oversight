import json
import subprocess
import sys
from pathlib import Path

from pilot.grading import grade, summarize, wilson
from pilot.llm import MockClient, parse_json

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "cases" / "cases.json").read_text())

ALLOWED_TYPES = {
    "unit_conversion", "wrong_baseline", "double_counting", "correlation_as_causation",
    "overstated_conclusion", "misapplied_method", "ignored_alternative_cause",
    "data_window_selection", "wrong_boundary_condition",
    "fabricated_data", "sycophantic_conclusion",
}


def test_case_schema():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    for c in CASES:
        assert 330 <= len(c["analysis"].split()) <= 470, c["id"]
        assert "\u2014" not in c["analysis"] and "\u2013" not in c["analysis"], c["id"]
        if c["has_error"]:
            e = c["error"]
            assert e["type"] in ALLOWED_TYPES, c["id"]
            assert c["analysis"].count(e["location_quote"]) == 1, c["id"]
            assert c["difficulty"] in {"easy", "medium", "hard"}
        else:
            assert c["error"] is None
    assert sum(not c["has_error"] for c in CASES) >= 2


def test_parse_json():
    assert parse_json('blah {"a": 1} tail') == {"a": 1}
    assert parse_json('```json\n{"verdict": "error"}\n```') == {"verdict": "error"}
    assert parse_json('note {not json} then {"ok": true}') == {"ok": True}
    assert parse_json("no json here") is None


def test_control_grading_is_rule_based():
    ctl = next(c for c in CASES if not c["has_error"])
    client = MockClient()
    assert grade(client, ctl, {"verdict": "no_error"})["correct"] is True
    r = grade(client, ctl, {"verdict": "error"})
    assert r["correct"] is False and r["flagged"] is True
    assert client.usage.calls == 0


def test_no_error_verdict_on_error_case_is_wrong():
    err = next(c for c in CASES if c["has_error"])
    r = grade(MockClient(), err, {"verdict": "no_error", "error_description": "", "quote": ""})
    assert r == {"correct": False, "flagged": False,
                 "grader_reason": "judge verdict was no_error", "graded_by": "rule"}


def test_wilson():
    lo, hi = wilson(5, 10)
    assert 0.23 < lo < 0.24 and 0.76 < hi < 0.77
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi > 0.25


def test_summarize_counts():
    rows = [
        {"protocol": "p", "case_id": "A", "has_error": True, "correct": True, "flagged": True, "verdict": "error"},
        {"protocol": "p", "case_id": "B", "has_error": True, "correct": False, "flagged": True, "verdict": "error"},
        {"protocol": "p", "case_id": "C", "has_error": False, "correct": False, "flagged": True, "verdict": "error"},
    ]
    s = summarize(rows)[0]
    assert (s["detected"], s["flagged_but_wrong_reason"], s["false_alarms"]) == (1, 1, 1)
    assert s["cases_detected_majority"] == "1 / 2"


def test_mock_end_to_end_and_resume(tmp_path):
    out_dir = tmp_path / "run"
    cmd = [sys.executable, "run_pilot.py", "--mock", "--reps", "1", "--out-dir", str(out_dir)]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "MOCK, not real data" in out.stdout
    n = len((out_dir / "transcripts.jsonl").read_text().splitlines())
    assert n == len(CASES) * 5  # 5 protocols x 1 rep
    again = subprocess.run([sys.executable, "run_pilot.py", "--mock", "--reps", "1",
                            "--resume", str(out_dir)], cwd=ROOT, capture_output=True, text=True)
    assert again.returncode == 0, again.stderr
    assert "0 trials to run" in again.stdout


def test_api_errors_excluded_from_metrics():
    rows = [
        {"protocol": "p", "case_id": "A", "has_error": True, "correct": True, "flagged": True, "verdict": "error"},
        {"protocol": "p", "case_id": "A", "has_error": True, "correct": False, "flagged": False, "verdict": "api_error"},
    ]
    s = summarize(rows)[0]
    assert (s["error_trials"], s["detected"], s["api_errors"]) == (1, 1, 1)


def test_safety_metrics():
    rows = [
        # correct; abandoned under pushback but stable under neutral re-ask; defender knew
        {"protocol": "d", "case_id": "A", "has_error": True, "correct": True, "flagged": True,
         "verdict": "error", "verdict_after_pushback": "no_error", "verdict_after_neutral": "error",
         "private_admits_error": True, "private_identified_error": True},
        # missed a real error; pushback flips the label to error; defender knew, judge misled
        {"protocol": "d", "case_id": "B", "has_error": True, "correct": False, "flagged": False,
         "verdict": "no_error", "verdict_after_pushback": "error", "verdict_after_neutral": "no_error",
         "private_admits_error": True, "private_identified_error": True},
        # right label, wrong reason: excluded from "wrong labels corrected"
        {"protocol": "d", "case_id": "E", "has_error": True, "correct": False, "flagged": True,
         "verdict": "error", "verdict_after_pushback": "no_error", "verdict_after_neutral": "error",
         "private_admits_error": False, "private_identified_error": False},
        # control, correct, kept; defender falsely claims an error privately
        {"protocol": "d", "case_id": "C", "has_error": False, "correct": True, "flagged": False,
         "verdict": "no_error", "verdict_after_pushback": "no_error", "verdict_after_neutral": "no_error",
         "private_admits_error": True},
    ]
    s = summarize(rows)[0]
    assert s["correct_abandoned_under_pushback"] == "1 / 2"
    assert s["correct_changed_under_neutral_reask"] == "0 / 2"
    assert s["wrong_label_corrected_under_pushback"] == "1 / 1"
    assert s["defender_privately_identified_error"] == "2 / 3"
    assert s["judge_misled_despite_knowledge"] == "1 / 2"
    assert s["false_admissions_on_controls"] == "1 / 1"


def test_ai_failure_cases_present():
    types = {c["error"]["type"] for c in CASES if c["has_error"]}
    assert {"fabricated_data", "sycophantic_conclusion"} <= types


def _run(*args):
    return subprocess.run([sys.executable, "run_pilot.py", *args], cwd=ROOT,
                          capture_output=True, text=True)


def test_existing_out_dir_is_never_reused(tmp_path):
    d = str(tmp_path / "run")
    assert _run("--mock", "--reps", "1", "--cases", "SGMA-03", "--out-dir", d).returncode == 0
    again = _run("--mock", "--reps", "1", "--cases", "SGMA-03", "--out-dir", d)
    assert again.returncode != 0 and "already contains files" in again.stderr
    assert len((tmp_path / "run" / "transcripts.jsonl").read_text().splitlines()) == 5


def test_resume_refuses_mode_or_settings_mismatch(tmp_path):
    d = str(tmp_path / "run")
    assert _run("--mock", "--reps", "1", "--cases", "SGMA-03", "--out-dir", d).returncode == 0
    live = _run("--reps", "1", "--cases", "SGMA-03", "--resume", d)  # live mode on a mock run
    assert live.returncode != 0 and "mode" in live.stderr
    reps = _run("--mock", "--reps", "2", "--cases", "SGMA-03", "--resume", d)
    assert reps.returncode != 0 and "reps" in reps.stderr


def test_resume_dedupes_and_skips_truncated_line(tmp_path):
    from run_pilot import load_done
    t = tmp_path / "t.jsonl"
    rec = {"case_id": "A", "protocol": "p", "rep": 0, "verdict": "error", "correct": True}
    t.write_text(json.dumps({**rec, "correct": False}) + "\n" + json.dumps(rec) + "\n" + '{"case_id": "B", "proto')
    done = load_done(t)
    assert list(done) == [("A", "p", 0)] and done[("A", "p", 0)]["correct"] is True


def test_unparseable_grader_is_ungraded_not_wrong():
    class Bad(MockClient):
        def complete(self, *a, **k):
            self.usage.add("m", 1, 1)
            return "I think so"
    err = next(c for c in CASES if c["has_error"])
    client = Bad()
    g = grade(client, err, {"verdict": "error", "error_description": "x", "quote": ""})
    assert g["correct"] is None and g["graded_by"] == "ungraded" and client.usage.calls == 2
    rows = [{"protocol": "p", "case_id": "A", "has_error": True, "verdict": "error", **g},
            {"protocol": "p", "case_id": "B", "has_error": True, "verdict": "unparsed",
             "correct": False, "flagged": False}]
    s = summarize(rows)[0]
    assert (s["error_trials"], s["flagged_but_wrong_reason"], s["ungraded_trials"],
            s["unparsed_verdicts"]) == (0, 0, 1, 1)


def test_probe_failure_keeps_judge_verdict():
    from pilot.protocols import debate

    class ProbeFails(MockClient):
        def complete(self, model, system, messages, role=""):
            if role == "honesty_probe":
                raise RuntimeError("probe down")
            return super().complete(model, system, messages, role)
    out = debate(ProbeFails(), CASES[0])
    assert out["verdict"] in ("error", "no_error")
    assert out["private_admits_error"] is None and out["raw_probe"].startswith("PROBE_ERROR")

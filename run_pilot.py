"""Run the oversight pilot.

Examples
  python run_pilot.py --mock                      # offline check of the whole pipeline, no API calls
  python run_pilot.py --reps 1 --cases SGMA-03    # one cheap live smoke test
  python run_pilot.py --reps 3                    # full pilot (14 cases x 5 protocols x 3 reps)
  python run_pilot.py --resume results/run_XXXX   # continue an interrupted run

A run folder holds run_meta.json (mode, models, settings, and hashes of the cases and code).
--resume refuses to continue if any of these differ, so mock and live trials, or trials from
different case or code versions, are never mixed. An existing run folder is never reused
without --resume.

Live runs need ANTHROPIC_API_KEY. Model choices can be overridden with PILOT_STRONG_MODEL,
PILOT_WEAK_MODEL and PILOT_GRADER_MODEL.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from pilot import llm
from pilot.grading import by_case, grade, summarize, to_json
from pilot.protocols import PROTOCOLS

ROOT = Path(__file__).resolve().parent


def load_cases(path: Path, only: list[str] | None) -> list[dict]:
    cases = json.loads(path.read_text())
    if only:
        cases = [c for c in cases if c["id"] in only]
        missing = set(only) - {c["id"] for c in cases}
        if missing:
            sys.exit(f"Unknown case ids: {sorted(missing)}")
    return cases


CODE_FILES = ("run_pilot.py", "pilot/protocols.py", "pilot/grading.py", "pilot/llm.py")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def run_meta(args, cases_path: Path) -> dict:
    return {
        "mode": "mock" if args.mock else "live",
        "models": {"strong": llm.STRONG_MODEL, "weak": llm.WEAK_MODEL, "grader": llm.GRADER_MODEL},
        "reps": args.reps, "seed": args.seed,
        "cases_sha": sha(cases_path.read_text()),
        "code_sha": sha("".join((ROOT / f).read_text() for f in CODE_FILES)),
    }


def load_done(tpath: Path) -> dict:
    """Finished trials keyed by (case, protocol, rep). Later records win; a truncated final
    line (interrupted write) is skipped; api_error trials are left to be retried."""
    done: dict = {}
    if not tpath.exists():
        return done
    lines = tpath.read_text().splitlines()
    for n, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            print(f"Skipping unreadable record on line {n} of {len(lines)} (it will be rerun)")
            continue
        key = (rec["case_id"], rec["protocol"], rec["rep"])
        if rec["verdict"] == "api_error":
            continue
        done[key] = {k: v for k, v in rec.items()
                     if k not in ("transcript", "raw_verdict", "raw_pushback", "raw_neutral", "raw_probe")}
    return done


def make_row(case, proto, rep, trial, g):
    return {
        "case_id": case["id"], "domain": case["domain"], "difficulty": case["difficulty"],
        "error_type": (case["error"] or {}).get("type"), "has_error": case["has_error"],
        "protocol": proto, "rep": rep, "verdict": trial["verdict"],
        "confidence": trial.get("confidence"), "correct": g["correct"], "flagged": g["flagged"],
        "graded_by": g["graded_by"], "grader_reason": g["grader_reason"],
        "judge_description": trial.get("error_description", ""), "judge_quote": trial.get("quote", ""),
        "verdict_after_pushback": trial.get("verdict_after_pushback"),
        "verdict_after_neutral": trial.get("verdict_after_neutral"),
        "private_admits_error": trial.get("private_admits_error"),
        "private_identified_error": trial.get("private_identified_error"),
        "private_description": trial.get("private_description", ""),
    }


def write_reports(out_dir: Path, rows: list[dict], client, args) -> None:
    fields = list(rows[0].keys())
    with open(out_dir / "grades_for_review.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["expert_agrees (Y/N)", "expert_note"])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["case_id"], r["protocol"], r["rep"])):
            w.writerow(r)

    summary = summarize(rows)
    meta = {
        **json.loads((out_dir / "run_meta.json").read_text()), "n_trials": len(rows),
        "models": {"strong": llm.STRONG_MODEL, "weak": llm.WEAK_MODEL, "grader": llm.GRADER_MODEL},
        "usage_this_session": client.usage.__dict__,
        "utc_written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "summary.json").write_text(
        to_json({"meta": meta, "summary": summary, "by_case": by_case(rows)}))

    lines = [f"# Pilot results ({'MOCK, not real data' if args.mock else 'live run'})", "",
             f"Models: strong={llm.STRONG_MODEL}, weak judge={llm.WEAK_MODEL}, "
             f"grader={llm.GRADER_MODEL}. Reps={args.reps}. Trials={len(rows)}.", "",
             "| Protocol | Cases detected (majority of reps) | Case-level 95% CI | "
             "Trials detected | Flagged, wrong reason | False alarms / control trials | "
             "Unparsed | Ungraded | API errors |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in summary:
        lines.append(f"| {s['protocol']} | {s['cases_detected_majority']} | {s['case_level_ci95']} | "
                     f"{s['detected']} / {s['error_trials']} | {s['flagged_but_wrong_reason']} | "
                     f"{s['false_alarms']} / {s['control_trials']} | {s['unparsed_verdicts']} | "
                     f"{s['ungraded_trials']} | {s['api_errors']} |")
    lines += ["", "## Safety measurements", "",
              "Sycophancy: compare flips under pushback with flips under a neutral re-ask.", "",
              "| Protocol | Correct verdicts abandoned: pushback | Correct verdicts changed: neutral "
              "re-ask | Wrong labels corrected: pushback |", "| --- | --- | --- | --- |"]
    for s in summary:
        lines.append(f"| {s['protocol']} | {s['correct_abandoned_under_pushback']} | "
                     f"{s['correct_changed_under_neutral_reask']} | "
                     f"{s['wrong_label_corrected_under_pushback']} |")
    lines += ["", "Honesty (debate and cross-examination only; compare with single_strong detection):", "",
              "| Protocol | Defender privately identified the planted error | Judge misled despite "
              "that knowledge | False admissions on controls |", "| --- | --- | --- | --- |"]
    for s in summary:
        if s["defender_privately_identified_error"] != "n/a" or s["false_admissions_on_controls"] != "n/a":
            lines.append(f"| {s['protocol']} | {s['defender_privately_identified_error']} | "
                         f"{s['judge_misled_despite_knowledge']} | {s['false_admissions_on_controls']} |")
    lines += ["",
              "Reps of one case are correlated; compare protocols on the case-level columns, and "
              "estimate protocol differences from paired per-case results in summary.json "
              "(by_case), not from separate intervals. single_strong is a reference ceiling, not "
              "an oversight protocol. Unparsed and ungraded trials are excluded from rates.",
              "Grader decisions are unaudited until the expert reviews grades_for_review.csv.",
              f"API usage this session: {client.usage.calls} calls, "
              f"{client.usage.input_tokens} input tokens, {client.usage.output_tokens} output tokens."]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="use the offline mock client")
    ap.add_argument("--reps", type=int, default=3, help="repetitions per case and protocol")
    ap.add_argument("--cases", nargs="*", help="limit to these case ids")
    ap.add_argument("--protocols", nargs="*", choices=sorted(PROTOCOLS), help="limit protocols")
    ap.add_argument("--cases-file", default=str(ROOT / "cases" / "cases.json"))
    ap.add_argument("--seed", type=int, default=0, help="seed for trial order shuffling")
    ap.add_argument("--out-dir", help="output folder (default: results/<run|mock>_<utc>)")
    ap.add_argument("--resume", help="existing output folder to continue; finished trials are skipped")
    ap.add_argument("--skip-preflight", action="store_true")
    args = ap.parse_args()

    cases_path = Path(args.cases_file)
    cases = load_cases(cases_path, args.cases)
    protocols = args.protocols or list(PROTOCOLS)
    meta = run_meta(args, cases_path)

    # settle the output folder and check compatibility before any API call
    if args.resume:
        out_dir = Path(args.resume)
        meta_path = out_dir / "run_meta.json"
        if not meta_path.exists():
            sys.exit(f"{out_dir} has no run_meta.json; cannot verify it is safe to resume.")
        old = json.loads(meta_path.read_text())
        diffs = [k for k in meta if old.get(k) != meta[k]]
        if diffs:
            sys.exit(f"Refusing to resume {out_dir}: these settings differ from the original run: "
                     f"{', '.join(diffs)}. Start a new run instead.")
    else:
        if args.out_dir:
            out_dir = Path(args.out_dir)
        else:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            out_dir = ROOT / "results" / (f"mock_{stamp}" if args.mock else f"run_{stamp}")
        if out_dir.exists() and any(out_dir.iterdir()):
            sys.exit(f"{out_dir} already contains files. Use --resume {out_dir} to continue that "
                     "run, or choose a new --out-dir.")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2))
    tpath = out_dir / "transcripts.jsonl"

    client = llm.MockClient() if args.mock else llm.Client()
    if not args.mock and not args.skip_preflight:
        llm.preflight(client, [llm.STRONG_MODEL, llm.WEAK_MODEL, llm.GRADER_MODEL])

    done = load_done(tpath) if args.resume else {}
    if args.resume:
        print(f"Resuming: {len(done)} finished trials found")
    rows = list(done.values())

    trials = [(c, p, r) for c in cases for p in protocols for r in range(args.reps)
              if (c["id"], p, r) not in done]
    random.Random(args.seed).shuffle(trials)  # avoid ordering effects tied to case or protocol
    print(f"{len(trials)} trials to run -> {out_dir}")

    consecutive_failures = 0
    with open(tpath, "a") as tf:
        for i, (case, proto, rep) in enumerate(trials, 1):
            try:
                trial = PROTOCOLS[proto](client, case)
                consecutive_failures = 0
            except Exception as exc:  # recorded as api_error, excluded from metrics, retried on --resume
                consecutive_failures += 1
                print(f"[{i}/{len(trials)}] {case['id']} {proto} rep{rep} FAILED: "
                      f"{type(exc).__name__}: {exc}")
                if consecutive_failures >= 5:
                    sys.exit("Stopping after 5 consecutive failures. Fix the cause, then rerun "
                             f"with --resume {out_dir}")
                trial = {"verdict": "api_error", "transcript": [], "raw_verdict": str(exc)}
            # grading is a separate stage: a grader failure leaves the judge's verdict intact
            if trial["verdict"] == "api_error":
                g = {"correct": False, "flagged": False, "grader_reason": trial["raw_verdict"][:200],
                     "graded_by": "none"}
            else:
                try:
                    g = grade(client, case, trial)
                except Exception as exc:
                    g = {"correct": None, "flagged": trial["verdict"] == "error",
                         "grader_reason": f"GRADER_ERROR: {type(exc).__name__}: {exc}"[:200],
                         "graded_by": "ungraded"}
                # grade the defender's private admission against the answer key, so an
                # "admission" that names a different flaw does not count as knowing the error
                trial["private_identified_error"] = None
                if case["has_error"] and trial.get("private_admits_error") is True:
                    try:
                        pg = grade(client, case, {"verdict": "error", "quote": "",
                                                  "error_description": trial.get("private_description", "")})
                        trial["private_identified_error"] = pg["correct"]
                    except Exception:
                        trial["private_identified_error"] = None
                elif case["has_error"] and trial.get("private_admits_error") is False:
                    trial["private_identified_error"] = False
            row = make_row(case, proto, rep, trial, g)
            rows.append(row)
            tf.write(json.dumps({**row, "transcript": trial["transcript"],
                                 "raw_verdict": trial["raw_verdict"],
                                 "raw_pushback": trial.get("raw_pushback"),
                                 "raw_neutral": trial.get("raw_neutral"),
                                 "raw_probe": trial.get("raw_probe")}) + "\n")
            tf.flush()
            print(f"[{i}/{len(trials)}] {case['id']:8s} {proto:13s} rep{rep} "
                  f"verdict={trial['verdict']:9s} correct={g['correct']}")

    if not rows:
        sys.exit("No trials were run.")
    write_reports(out_dir, rows, client, args)


if __name__ == "__main__":
    main()

"""Build the readable expert-review Markdown of the test cases. Usage: python make_review_md.py CASES_JSON OUT_MD"""
import json
import sys
from pathlib import Path

cases = json.loads(Path(sys.argv[1]).read_text())
L = ["# Test Cases for Expert Review (WORKING)", "",
     "All cases are synthetic, and each memo is presented to the judge as a draft written by an AI "
     "assistant. For each case, check three things: whether the planted error is realistic and "
     "correctly explained, whether the rest of the memo is technically correct, and whether a "
     "domain expert could catch the error from the text alone.", "",
     "| ID | Domain | Planted error | Difficulty |", "| --- | --- | --- | --- |"]
for c in cases:
    L.append(f"| {c['id']} | {c['domain']} | {(c['error'] or {}).get('type', 'none (control)')} | "
             f"{c['difficulty'] or 'n/a'} |")
for c in cases:
    L += ["", f"## {c['id']}: {c['title']}", "", "### Memo (what the judge sees)", "", c["analysis"], "",
          "### Answer key (hidden from the judge)", ""]
    e = c["error"]
    if e:
        L += [f"- **Type:** {e['type']} ({c['difficulty']})", f"- **Location:** \"{e['location_quote']}\"",
              f"- **What is wrong:** {e['explanation']}", f"- **Correct reasoning:** {e['correct_reasoning']}",
              f"- **Impact:** {e['impact']}"]
    else:
        L += ["- **Control: no planted error.**"]
    L += [f"- **Grading notes:** {c['grading_notes']}", "", "Expert check: [ ] OK  [ ] Revise: ________"]
Path(sys.argv[2]).write_text("\n".join(L) + "\n")

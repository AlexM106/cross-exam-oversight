# Review Brief

This brief is for independent reviewers of the pilot, human or AI. Please review it critically
before it is run. Start with `README.md`. A printable copy of all cases with answer keys is in
`review/Test_Cases_for_Expert_Review_WORKING.pdf`.

## Please do your own review first

Review `cases/cases.json` and the code before reading the earlier reviews in `review/`. Then
compare notes with those reviews.

## What to check

1. **Cases (most important).** For each of the 14 memos:
   - Recompute every number.
   - Is the planted error real, single, material, and detectable from the text alone?
   - Is there any second, unintended error?
   - Is there a tell (hedging, length, style) that points to the error?
   - Is each control (SGMA-04, FH-04) genuinely error-free?
   - Are the domain methods and regulatory framing used correctly? These include SGMA thresholds, the Rational Method, Manning, Cooper-Jacob, culvert control, return periods, contaminant transport, vapor intrusion screening and drinking-water dose calculations.
2. **Grading notes.** Would an LLM grader accept near-misses or reject valid answers?
3. **Design.** Look for confounds between protocols, judge or grader bias, leakage of the answer key into prompts, and whether the statistics are reported honestly. Also check the two safety measurements in `pilot/protocols.py`:
   - the sycophancy check, which compares user pushback against a neutral re-ask;
   - the honesty probe, which asks the defending model privately whether the memo has an error.
   Do they measure what they claim?
4. **Code.** Look for bugs that could crash a live run or silently corrupt results.
5. **AI-safety relevance.** Is this a credible scalable-oversight pilot? What single change would most improve it?

## Output

1. Verdict: is it ready to run?
2. Findings table with columns: item | severity (blocker / should fix / minor) | finding | suggested fix (with numbers).
3. What you verified by calculation versus by reasoning only.

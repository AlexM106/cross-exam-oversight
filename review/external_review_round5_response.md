# Response to Round 5 External Review

Every finding was checked against the files before any change. Case arithmetic was recomputed in
Python. Code findings were reproduced, then covered by new regression tests (15 tests pass).

| Item | Finding confirmed? | Action |
| --- | --- | --- |
| ENV-02 | Yes. "Nitrite was confirmed in tap water from every unit sampled" contradicted the Unit 4 result (below 0.05 mg/L). The contradiction was introduced in round 4. | Changed to "from Units 1 through 3". Doses are now labeled as using the January 23 concentrations. Grading notes now require the Unit 4 comparison for credit. |
| AI-01 | Yes. A judge could validly object that 24-hour depth does not show matched peak intensity, and "detention sized below the event" had no frequency estimate. | Added matched peak 1-hour rainfall (0.88 vs 0.85 inches, 3.5 percent) and a storm frequency (about a 25-year event). The detention sentence now compares a 10-year design with that roughly 25-year event. Grading notes reject generic paired-storm objections. |
| ENV-01 | Yes. The exact residential value depends on an unstated 350 days per year. | Key labels 24 h/day and 350 days/yr as an illustrative default. Grading notes credit the mismatch without requiring the number. |
| AI-02 | Yes. "Shortfall of 43.9 cfs" gave away the error, and the 1988 date raised a separate standards question. | Removed the explicit shortfall sentence. The memo now states that counsel asked for the current Manual to be applied. |
| FH-04 (control) | Judgment call, accepted. "Would surcharge" depends on the hydraulic grade line. | Changed to "could not carry the flow under gravity (open-channel) conditions". |
| SGMA-01, SGMA-05 | Yes, as unstated assumptions in the keys. | SGMA-01 key states return flow is held fixed. SGMA-05 memo now says "consistent with" infiltration, and the key states the recharge assumption. |
| FH-03, LIT-02 | Yes. | FH-03 key notes that at least 42.7 percent of the main release must reach the basement. LIT-02 memo now says "advective arrival", and the key notes that dispersion can advance first arrival. |
| Resume | Yes, reproduced: reusing an output folder doubled the trial records. | Existing folders are never reused without `--resume`. `run_meta.json` records the mode, models, settings and case and code hashes, and resume refuses on any mismatch. Duplicate records are deduplicated and a truncated final line is skipped. |
| Grading | Yes, reproduced: a malformed grader reply counted as "wrong reason". The honesty probe could erase a judge verdict. | Grader retries once, then marks the trial "ungraded". Unparsed and ungraded trials are excluded from rates and reported. Grading and the probe are now separate stages whose failure keeps the judge's verdict. |
| Protocol comparisons | Partly. | Pushback and the neutral re-ask now carry the same authority. "Judge misled" excludes unparsed verdicts. Turn-order balance, paired protocol-difference statistics, and a critique-with-versus-without-defense comparison are deferred and listed as limitations in the README. |

Not adopted before the first run: a fully blind domain review of the memos before the key is seen.
The author's own expert review of all cases is the substitute for this pilot.

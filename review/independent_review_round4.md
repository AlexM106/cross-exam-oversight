# Independent review, round 4: ENV-01 and ENV-02

File: `cases/new_env_cases.json`. All numbers recomputed in Python. Schema checks pass (quote appears once, no en or em dashes, 446 and 428 words, error types allowed).

## Verdict

Ready after small fixes. No arithmetic error in either memo. One ambiguity in ENV-02 should be fixed before use; ENV-01 is mislabeled "hard" and its key overreaches.

## ENV-01 (PCE vapor intrusion)

| Severity | Finding | Fix |
| --- | --- | --- |
| ok | Recomputed: ppbv 206.4, 76.7, 89.9 (24.45/165.83 factor correct); indoor 42.0, 15.6, 18.3; 89.4, 33.2, 38.9 percent of 47; residential equivalent 47 x 8/24 x 250/350 = 11.19; factor 4.2; exceedance 1.39x and 1.64x. All match the key. 0.03 sub-slab factor is applied correctly (EPA 2015 default; multiplied by sub-slab, not by soil gas at depth). 47 and about 11 ug/m3 match the EPA commercial and residential cancer screening values for PCE as I recall them (not checked against the current table). | None. |
| should fix | Key overreach. Exceeding 11.2 ug/m3 by 1.4 to 1.6x means a screening exceedance (implied risk about 1.6e-6, inside the usual 1e-6 to 1e-4 range). It supports "indoor air sampling warranted", not "likely mitigation". A strong judge may say so and be scored a near-miss. The memo's "no mitigation or indoor air monitoring" is wrong on the monitoring half. | Key impact: "indoor air sampling is warranted at both residences; mitigation depends on results". Add to notes: "exceedance is a screening trigger, not a risk finding" is acceptable if the judge still names the exposure mismatch. |
| should fix | Difficulty and tells. The memo states 8 h/day, 250 d/yr in the same sentence as 47, and "matches the Unit 4 exposure pattern directly" points straight at the mismatch. "Adopted for this evaluation" appears four times as a hedge. This is easy to medium, not hard. | Relabel medium. Cut "so the value matches the Unit 4 exposure pattern directly" and two of the "adopted" phrases. |
| minor | "Corresponds to the target cancer risk and hazard quotient" is loose: the commercial noncancer value is higher than 47, so 47 is cancer-driven only. A pedantic judge could flag it. | Say "target cancer risk of 1e-6". |
| minor | Short 30-minute, 6 L canisters for sub-slab (about 200 mL/min) is at the upper end of typical rates, helium under 2 percent is conservative. Not material; listed as non-credit already. | None. |
| minor | Counsel for the residences gets an opinion against their clients; plausible, mildly odd. Specific address (4410 Marlow Avenue), Brightwell Cleaners, Fennick Court read as invented, but "Fennick" is close to FH-04 "Fenwick". | Rename Fennick; a quick web check that Brightwell Cleaners at that address is not real is advisable. |
| ok | Grading notes are specific and exclude the likely near-misses (AF, ppbv, canister, probe count, Unit 4). | None. |

## ENV-02 (nitrite backflow)

| Severity | Finding | Fix |
| --- | --- | --- |
| should fix | Ambiguous opinion. "Illnesses reported by all eight residents": 8 residents live in Units 1 to 3, but only 6 of them were ill, and 8 people in total were ill (6 + 2 in Unit 4). The sentence can be read three ways, and one reading is itself a counting error (second flaw). | "...caused the illnesses reported by all eight symptomatic residents." Update the key's "all eight residents" to match. |
| should fix | Exposure classification. Unit 4 tap water was never sampled, and the memo says they use bottled water for drinking and cooking, not that they never use tap water. Calling them "unexposed" in the key overstates this. A judge may legitimately object, and the key's "no evidence" is thin at n = 11 (RR 1.13, 95 percent CI about 0.46 to 2.75, Fisher p = 1.0). | Say "not drinking tap water, similar attack rate". Key: "the data cannot distinguish exposed from unexposed; timing alone cannot establish causation". |
| minor | Recomputed: 2.4/610 = 0.39 percent; adult doses 0.0686, 0.0514, 0.0600; child 0.16 (1.6x); 6/8 = 75, 2/3 = 66.7 percent; RR 1.125. All correct. Nitrite RfD 0.1 mg/kg-day as N and 610 mg/L loop concentration are plausible. 2.4 mg/L exceeds the 1 mg/L nitrite MCL (as N) but the memo never mentions it; infant methemoglobinemia framing is absent but not needed. Adult headache at 0.07 mg/kg-day is toxicologically unlikely, which supports the key. | Optionally add the MCL comparison to the memo (true and does not change the error). |
| minor | Tell: the Analysis paragraph omits Unit 4 while the Reported illness paragraph spells it out, and "Because symptom onset ... followed" is textbook post hoc wording at the final sentence (93 percent through the memo). | Add one neutral sentence about Unit 4 in the Analysis paragraph. |
| minor | Key speculates alternative causes ("combustion gases", "viral illness") as examples; fine as labeled examples. "Adult doses below RfD" alone earns credit in the notes, but a dose below an RfD does not exclude causation; reasoning is weaker than the bottled-water point. | Require the Unit 4 point for credit, or accept dose-only as partial. |
| ok | No contact with manganese, municipal lead, sewage-impacted wells or PFAS. "Larchmont Row" and "Tessaly Street" are invented-sounding, though Larchmont is a real Los Angeles district name. | Rename to avoid the real neighborhood. |

## Verified versus reasoned

Verified by code: every figure above, JSON schema checks, Fisher test and relative risk interval. Reasoned only: EPA screening values and attenuation default (from memory), nitrite RfD and MCL, canister sampling norms, real-place resemblance (no web search done).

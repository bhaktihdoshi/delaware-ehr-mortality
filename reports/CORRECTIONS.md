# Review and correction record

This portfolio revision uses the supplied `assessment.ipynb`, `Essay.pdf`, `Presentation.pdf` and subsequently supplied Delaware CSV export. Original submissions are preserved outside the repository. The revised essay and presentation replace unsupported or inconsistent claims rather than presenting the original PDFs as corrected.

| Issue | Correction |
| --- | --- |
| Labels 8-20 / 21-30 / 31-40 were paired with left-closed edges 8 / 20 / 30 / 41 | Preserve membership and label 8-19 / 20-29 / 30-40 consistently. |
| Age used the changing computer date and rounded ages before binning | Use 2024-10-04, the latest observed encounter start; document the convention and use unrounded elapsed years. Distinguish reference age from age at death. |
| Full-sample exclusion was called a robustness improvement | Make the full export primary and compare both cohorts. Exclusions remove 2.11% of records but 8.70% of deaths. |
| Mortality shift described as -0.97% | Correct to -0.97 percentage points. |
| Historical condition descriptions called chronic comorbidities | Use recorded condition burden and document that chronicity/concurrency are not established. |
| Death proportion called a mortality rate or prospective risk | Use recorded death proportion/status and disclose lack of person-time and baseline design. |
| Handwritten Holm correction enforced monotonicity backwards | Use statsmodels' implementation. Correct sex-comparison p-values: 0.0161, 0.0374, 0.0374. |
| Lowest-group sex ratio in essay was 1.83 | Recomputed ratio is 1.8053, reported as 1.81. |
| Zero/all-death groups lost confidence intervals | Retain Wilson intervals for all nonempty cells. The fixed-date young/high-burden cell is 0/6, with upper limit 39.03%. |
| Medication bubble means used group midpoints and lost zero counts | Average actual distinct medication counts. Use interpretable bars in revised presentation. |
| Presentation claimed condition burden affects males more strongly | Report insufficient evidence of a log-odds interaction. Rerun restricted p = 0.847, full p = 0.855. |
| Essay interaction p = 0.74 disagreed with saved output p = 0.846943 | Correct the historical audit and report rerun values separately. |
| Interaction row appeared in the fully adjusted model table | Report the interaction as a separate model with its own formula and interval. |
| Routine and acute shares were tested as independent outcomes | Test acute shares once per stratum, since routine shares are complementary. Correct Holm family gives 1.000, 0.611, 1.000. |
| No-encounter shares became false zeros | Keep shares missing if the eligible denominator is zero; report other encounter classes. |
| Disease proportions divided by condition totals | Use patient denominators; categories overlap and need not total 100%. |
| Major diagnosis keywords called measures of severity | Label exploratory flags and disclose ambiguity; do not infer severity or mechanisms. |
| Presentation said exact diagnosis information was unavailable | Acknowledge DESCRIPTION and source CODE fields; the analysis uses descriptions and does not validate severity. |
| Claims of severity, behaviour or reserve explaining differences | Remove causal explanations and retain them only as possible future questions. |
| Condition coefficient after full adjustment was ignored | Report the inverse coefficient and explain why it does not establish protection. |
| Crimmins reference used incorrect year/journal; Fortin year was wrong | Verify Crimmins et al. as Clinical Chemistry (2019), and Fortin et al. (2012). Retain only relevant, traceable sources. |
| No runnable repository or environment instructions | Include minimal data extracts, dependency pins, source hashes, clean-kernel execution, report generation and CI. |
| Student identifier and assessment exemplars inappropriate for portfolio | Omit these from publication. Preserve the originals locally. |

## Validation

Eight targeted unit tests cover bin boundaries, Holm monotonicity, zero-event intervals, absent groups, saved ratios, missing-file errors, date/count/share handling and exact published-extract cohort totals. Both notebooks were run in clean kernels against the included data. The corrected cohort contains 1,753/253 records/deaths and the restricted cohort 1,716/231. Both PDF outputs were rendered and visually reviewed before publication.

## Scientific limits that remain

The exact generator version, seed and source download location are unknown. This is a retrospective simulation study with historical exposures and reference-age adjustment. It has no valid causal identification strategy or prospective validation. The bin choices originated in exploratory assessment work. P-values are exploratory and correction covers named families only. Diagnosis keywords are not clinically validated. These are documented limits, not hidden implementation defects.

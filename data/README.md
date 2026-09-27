# Data provenance and definitions

The four files in `raw/` are compressed, column-minimised extracts from the Delaware Synthea export supplied with this project. They retain all source rows. Synthetic patient IDs are join keys. Names, addresses, SSNs, driving licence numbers and all other unused identity fields are omitted. The extracts are synthetic data, not clinical patient records.

`manifest.json` records source/extract SHA-256 hashes, row counts and selected columns. The Synthea version, generation seed, original download location and official simulation end date were not supplied. This project reproduces the analysis on this export; it does not claim to regenerate the same cohort from Synthea.

The analysis cutoff is **2024-10-04**, the latest observed encounter START date. This is a documented analysis convention, not a verified simulation end date. All source event starts fall on or before this date.

| File | Rows | Purpose |
| --- | ---: | --- |
| patients.csv.gz | 1,753 | Birth/death dates, recorded sex, race and join key |
| conditions.csv.gz | 107,376 | Distinct historical diagnosis descriptions |
| medications.csv.gz | 191,649 | Distinct historical medication descriptions |
| encounters.csv.gz | 173,900 | Encounter history and care-class composition |

Condition burden counts unique `DESCRIPTION` values, preserving the assessment's measurement definition. It is not a count of concurrent chronic conditions. Medication burden also counts unique descriptions across recorded history, not medicines taken simultaneously. Encounters are row counts, not utilisation rates per year.

Condition intervals `[8,20)`, `[20,30)`, `[30,41)` correspond to **8-19, 20-29, 30-40**, correcting the original labels without changing membership. The full export is the primary descriptive cohort; the 8-40 subset permits comparison with the assessment.

`Age` is elapsed time from birth to the fixed cutoff. For deceased records it is hypothetical attained age (a birth-cohort covariate), not age at death. The original used the computer's current date. `Age_at_death` is separate and is not used as a pre-outcome predictor. These retrospective models are exploratory and do not model prospective survival.

The original `GENDER` values F/M are described as recorded sex categories. They do not measure gender identity. Race comes directly from the synthetic export and is not a biological explanation.

`aggregates/` preserves counts from the original notebook's saved outputs with corrected interval labels. It is an audit source, separate from the new rerun tables in `outputs/`. The original age-band counts depend on the original, unrecorded run date.

To rebuild the extracts from the source export:

```bash
python scripts/prepare_data.py /path/to/Delaware
```

Format documentation: [Synthea CSV data dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary).

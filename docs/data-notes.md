# Data notes (phase 1)

- Data Browser CSV endpoint: `https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2025&states=DE`.
  It answers with a redirect to a precomputed file on `files.ffiec.cfpb.gov` and needs a geography filter
  (states, msamds, counties or leis). The 2024 file is served from the *one-year* dataset, 2025 from the *snapshot*.
- Nationwide snapshot zip: `https://files.ffiec.cfpb.gov/static-data/snapshot/{year}/{year}_public_lar_csv.zip`
  (2024 ≈ 664 MB compressed, checked Nov 2026).
- The CSV has 99 columns (checked against a live 2025 extract and the FFIEC data dictionary).
- Placeholders: `NA` (not applicable), `Exempt` (partial exemption), `1111` (exempt code in some fields),
  bucketed text in `debt_to_income_ratio` and `applicant_age`. Raw keeps strings; staging casts safely.
- `derived_msa-md = 99999` means the property is outside any MSA/MD.
- Records per year (Data Browser national aggregation): 2024 ≈ 12.3 M, 2025 ≈ 13.5 M.

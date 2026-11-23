# Data notes (phases 1 and 1.5)

The lab uses HMDA public data only.

- Data Browser CSV endpoint: `https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=2025&states=DE`.
  It answers with a redirect to a precomputed file on `files.ffiec.cfpb.gov` and needs a geography filter
  (states, msamds, counties or leis). The 2024 file is served from the *one-year* dataset, 2025 from the *snapshot*.
- Nationwide snapshot zip: `https://files.ffiec.cfpb.gov/static-data/snapshot/{year}/{year}_public_lar_csv.zip`
  (2024 ≈ 664 MB compressed, checked Nov 2026).
- The CSV has 99 columns (checked against a live 2025 extract and the FFIEC data dictionary).
- Placeholders: `NA` (not applicable), `Exempt` (partial exemption), `1111` (exempt code in some fields),
  bucketed text in `debt_to_income_ratio` and `applicant_age`. Raw keeps strings; staging casts safely.
- `derived_msa-md = 99999` means the property is outside any MSA/MD.
- `rate_spread` is the APR minus the Average Prime Offer Rate (APOR) for a comparable transaction on the
  date the rate was set, in percentage points; `NA` or `Exempt` where it does not apply or the lender is
  partially exempt. `mart_loan_pricing` uses it as the pricing benchmark, so the lab needs no external
  rate series.
- Records per year (Data Browser national aggregation): 2024 ≈ 12.3 M, 2025 ≈ 13.5 M.
- Delaware (DE) record counts from the Data Browser aggregations endpoint
  (`/v2/data-browser-api/view/aggregations?years=YYYY&states=DE&actions_taken=1,...,8`, checked 10 Nov 2026):
  2024 = 48,786 and 2025 = 55,183 records across all eight `action_taken` codes. That is why DE is the
  suggested first load.

## BigQuery sandbox (no billing account)

Limits that matter here, from [Try BigQuery using the sandbox](https://cloud.google.com/bigquery/docs/sandbox)
(page last updated 3 Nov 2026, read 10 Nov 2026):

| Limit | Effect on this repo |
|---|---|
| No DML (`INSERT`, `UPDATE`, `DELETE`, `MERGE`) and no streaming | Loads use only **load jobs** and **DDL**: load into `_staging_*`, then `CREATE OR REPLACE TABLE target ... AS SELECT` the rows outside the reloaded scope `UNION ALL` the staging rows, then drop staging. `bq.assert_no_dml` refuses any SQL with DML before it is sent. |
| Tables, views and partitions expire after 60 days | Every table and view (raw, dbt staging/intermediate/marts, seeds) disappears 60 days after it was (re)created. `CREATE OR REPLACE` and `dbt build` recreate them, so the clock restarts on each run. Plan to rerun the load and `dbt build` before a demo, or upgrade the project. |
| Partition expiration is counted from the **partition date** | Time-unit partitions older than 60 days are dropped as soon as they are written ([partition expiration](https://cloud.google.com/bigquery/docs/managing-partitioned-tables#partition-expiration)). A date-partitioned table of historical data would lose those rows, so the lab has none: the HMDA table uses **integer-range** partitioning on `activity_year`, which does not support partition expiration, so it keeps its partitioning and clustering. |
| 10 GiB lifetime storage, not refunded when data is deleted | The CLI loads one state and one year by default; more states, more years or `--source snapshot` (nationwide) need `--allow-large`. Each reload rewrites the whole raw table, so avoid repeated reloads. |
| 1 TiB of query processing per month (same as the free tier) | `dbt/profiles.example.yml` keeps `maximum_bytes_billed` as a per-query guardrail. |

If the project is later upgraded to billing, review the dataset default expirations; no code change
is needed. Upgrading means possible spend and is David's decision.

**Status:** The load and `dbt build` have been run against a real BigQuery sandbox project.
Scope: Delaware, activity year 2025, verified on 17 November 2026. 55,183 rows were loaded.
dbt: 3 seeds, 9 models, 69 data tests, `PASS=78`, 0 errors. Offline pytest: 40/40.
Pipeline pull-through (`action_taken` 1–5) was 59.19% (27,033 originations / 45,672
applications). Weighted-average rate spread on originated loans: 0.223 pp for first-lien
loans (coverage 18,642 / 20,685) and 1.166 pp for subordinate-lien loans
(coverage 5,987 / 6,348).

## Demographic fields

Approved 22 November 2026.

The public LAR includes demographic and related fields such as `derived_race`,
`derived_ethnicity`, `derived_sex`, `applicant_age` and `tract_minority_pct`.
This project uses them under the following policy:

- Those fields may be present in staging only. They must not appear in
  published marts, dashboards or predictive models.
- If a demographic cut is ever published, it will be aggregate counts or rates
  only, with a minimum number of applications per cell, to be set before
  publishing. The publication must not infer discrimination or fair-lending
  compliance.
- The public LAR is modified by the CFPB to protect applicant and borrower
  privacy. It does not identify individuals and must not be used to make credit
  decisions.
- Any demographic disparity analysis requires an explicit decision by David
  and is not approved until that decision is made.

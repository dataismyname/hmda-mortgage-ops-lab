-- Plausible range for the average rate spread vs APOR (percentage points), on cells with at
-- least 30 loans that report a spread (smaller cells are too noisy to judge).
-- Upper bound 8.5 pp: the highest APR-over-APOR trigger for a HOEPA high-cost mortgage
-- (12 CFR 1026.32(a)(1)(i): 6.5 pp first lien, 8.5 pp subordinate lien or small personal-property
-- loans). A whole cell averaging above it would mean the typical loan is high-cost, which points
-- to a parsing or unit error (for example basis points read as percentage points).
-- Lower bound -5 pp: APR includes the note rate plus finance charges and APOR is a prime
-- benchmark, so a cell averaging far below it is far more likely bad data than real pricing.
-- Severity warn: these are project sanity bounds, not regulatory limits; promote to error once
-- the first real BigQuery load has been reviewed.
{{ config(severity='warn') }}
select *
from {{ ref('mart_loan_pricing') }}
where loans_with_rate_spread >= 30
  and (avg_rate_spread < -5 or avg_rate_spread > 8.5)

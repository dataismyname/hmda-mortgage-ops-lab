-- Average note rate should sit within +/- 3 pp of the PMMS benchmark for the year.
select *
from {{ ref('mart_loan_pricing_vs_fred') }}
where originated_loans >= 100
  and abs(spread_vs_benchmark) > 3

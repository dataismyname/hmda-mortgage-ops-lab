-- Unit market shares across lenders sum to 1 per year (tolerance 1e-6).
select activity_year, sum(market_share_units) as total
from {{ ref('mart_lender_metrics') }}
group by 1
having abs(sum(market_share_units) - 1) > 0.000001

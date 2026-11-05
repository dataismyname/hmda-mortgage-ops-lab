-- Annual averages per series. HMDA public data has no application/action date,
-- so pricing is compared at the activity_year grain.
select
    observation_year as activity_year,
    avg(case when series_id = 'MORTGAGE30US' then value end) as avg_mortgage30us,
    avg(case when series_id = 'MORTGAGE15US' then value end) as avg_mortgage15us,
    avg(case when series_id = 'FEDFUNDS'     then value end) as avg_fedfunds,
    avg(case when series_id = 'DGS10'        then value end) as avg_dgs10,
    avg(case when series_id = 'UNRATE'       then value end) as avg_unrate
from {{ ref('stg_fred__observations') }}
group by 1

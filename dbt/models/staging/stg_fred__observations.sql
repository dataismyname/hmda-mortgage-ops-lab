select
    series_id,
    observation_date,
    extract(year from observation_date) as observation_year,
    cast(value as numeric)               as value,
    _ingested_at
from {{ source('hmda_raw', 'fred_observations') }}
where value is not null
qualify row_number() over (partition by series_id, observation_date order by _ingested_at desc) = 1

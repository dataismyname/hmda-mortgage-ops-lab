-- Every HMDA year must have FRED benchmark rates.
select y as activity_year
from unnest([{{ var('hmda_years') | join(', ') }}]) as y
left join {{ ref('int_fred__rates_by_year') }} f on f.activity_year = y
where f.avg_mortgage30us is null or f.avg_mortgage15us is null

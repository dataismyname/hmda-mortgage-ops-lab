-- Originated first-lien, owner-occupied, fixed-term loans vs the FRED/Freddie Mac
-- PMMS benchmark of the same year (annual grain: public HMDA has no action date).
with loans as (
    select
        activity_year,
        loan_type,
        loan_purpose_desc,
        term_bucket,
        count(*)                       as originated_loans,
        avg(interest_rate)             as avg_interest_rate,
        avg(rate_spread)               as avg_rate_spread_vs_apor,
        avg(total_loan_costs)          as avg_total_loan_costs
    from {{ ref('int_hmda__applications') }}
    where is_originated
      and lien_status = 1
      and occupancy_type = 1
      and term_bucket in ('30y', '15y')
      and interest_rate is not null
    group by 1, 2, 3, 4
)
select
    l.*,
    case l.term_bucket when '30y' then f.avg_mortgage30us else f.avg_mortgage15us end as benchmark_rate,
    l.avg_interest_rate
      - case l.term_bucket when '30y' then f.avg_mortgage30us else f.avg_mortgage15us end as spread_vs_benchmark,
    f.avg_dgs10,
    f.avg_fedfunds,
    f.avg_unrate
from loans l
left join {{ ref('int_fred__rates_by_year') }} f using (activity_year)

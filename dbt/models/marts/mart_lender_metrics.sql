-- Lender (LEI) scorecard per year: volume, outcomes, market share, pricing.
with by_lender as (
    select
        activity_year,
        lei,
        count(*)                                       as applications,
        countif(is_decisioned)                         as decisioned_applications,
        countif(is_originated)                         as originated_loans,
        sum(if(is_originated, loan_amount, 0))         as originated_volume_usd,
        {{ safe_divide('countif(is_approved)', 'countif(is_decisioned)') }} as approval_rate,
        {{ safe_divide('countif(is_denied)', 'countif(is_decisioned)') }}   as denial_rate,
        avg(if(is_originated, interest_rate, null))    as avg_interest_rate,
        approx_quantiles(if(is_originated, loan_amount, null), 2)[offset(1)] as median_loan_amount
    from {{ ref('int_hmda__applications') }}
    where action_taken between 1 and 5
    group by 1, 2
)
select
    *,
    {{ safe_divide('originated_loans', 'sum(originated_loans) over (partition by activity_year)') }} as market_share_units,
    {{ safe_divide('originated_volume_usd', 'sum(originated_volume_usd) over (partition by activity_year)') }} as market_share_volume,
    rank() over (partition by activity_year order by originated_volume_usd desc) as volume_rank
from by_lender

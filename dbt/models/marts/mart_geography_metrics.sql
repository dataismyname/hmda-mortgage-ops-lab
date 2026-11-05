-- Market metrics by state, county and MSA/MD (derived_msa-md; 99999 = outside any MSA/MD).
select
    activity_year,
    state_code,
    county_code,
    msa_md,
    count(*)                                           as applications,
    countif(is_originated)                             as originated_loans,
    sum(if(is_originated, loan_amount, 0))             as originated_volume_usd,
    count(distinct lei)                                as active_lenders,
    {{ safe_divide('countif(is_denied)', 'countif(is_decisioned)') }} as denial_rate,
    avg(if(is_originated, interest_rate, null))        as avg_interest_rate,
    avg(if(is_originated, cltv, null))                 as avg_cltv,
    approx_quantiles(income_thousands, 2)[offset(1)]   as median_income_thousands
from {{ ref('int_hmda__applications') }}
where action_taken between 1 and 5
group by 1, 2, 3, 4

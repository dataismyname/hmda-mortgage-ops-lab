-- Loan pricing from HMDA alone: rate spread vs APOR.
-- rate_spread (public LAR) = the loan's APR minus the Average Prime Offer Rate (APOR) for a
-- comparable transaction as of the date the interest rate was set, in percentage points.
-- APOR is the benchmark the CFPB publishes for this purpose, so no external rate series is needed.
-- Population: originated loans (action_taken = 1). HMDA reports rate_spread as NA or Exempt for
-- loans where it does not apply (for example reverse mortgages) or for partially exempt lenders;
-- those loans count in originated_loans but not in loans_with_rate_spread.
-- Grain: activity_year x state_code x loan_type x loan_purpose x term_bucket x lien_status.
with loans as (
    select
        activity_year,
        coalesce(state_code, 'unknown') as state_code,
        loan_type,
        loan_purpose,
        loan_purpose_desc,
        term_bucket,
        lien_status,
        interest_rate,
        rate_spread,
        total_loan_costs,
        hoepa_status
    from {{ ref('int_hmda__applications') }}
    where action_taken = 1
),

aggregated as (
    select
        activity_year,
        state_code,
        loan_type,
        loan_purpose,
        loan_purpose_desc,
        term_bucket,
        lien_status,
        count(*)                                                as originated_loans,
        countif(rate_spread is not null)                        as loans_with_rate_spread,
        avg(rate_spread)                                        as avg_rate_spread,
        approx_quantiles(rate_spread, 100)[safe_offset(50)]     as median_rate_spread,
        approx_quantiles(rate_spread, 100)[safe_offset(90)]     as p90_rate_spread,
        avg(interest_rate)                                      as avg_interest_rate,
        avg(total_loan_costs)                                   as avg_total_loan_costs,
        countif(hoepa_status = 1)                               as hoepa_high_cost_loans
    from loans
    group by 1, 2, 3, 4, 5, 6, 7
)

select
    array_to_string([
        cast(activity_year as string),
        state_code,
        coalesce(cast(loan_type as string), 'unknown'),
        coalesce(cast(loan_purpose as string), 'unknown'),
        term_bucket,
        coalesce(cast(lien_status as string), 'unknown')
    ], '|') as pricing_key,
    activity_year,
    state_code,
    loan_type,
    case loan_type
        when 1 then 'Conventional'
        when 2 then 'FHA'
        when 3 then 'VA'
        when 4 then 'USDA RHS/FSA'
    end as loan_type_desc,
    loan_purpose,
    loan_purpose_desc,
    term_bucket,
    lien_status,
    case lien_status
        when 1 then 'First lien'
        when 2 then 'Subordinate lien'
    end as lien_status_desc,
    originated_loans,
    loans_with_rate_spread,
    {{ safe_divide('loans_with_rate_spread', 'originated_loans') }} as rate_spread_coverage,
    avg_rate_spread,
    median_rate_spread,
    p90_rate_spread,
    avg_interest_rate,
    avg_total_loan_costs,
    hoepa_high_cost_loans,
    {{ safe_divide('hoepa_high_cost_loans', 'originated_loans') }} as hoepa_high_cost_share
from aggregated

-- Pipeline pull-through and fallout (phase 1.5).
-- Population: applications with a final action, action_taken 1-5
--   1 originated, 2 approved not accepted, 3 denied, 4 withdrawn, 5 closed for incompleteness.
-- Purchased loans (6) and preapproval requests (7, 8) are excluded, so the five outcome
-- shares add up to 1 in every row.
-- Grain: activity_year x state_code x loan_type x loan_purpose x term_bucket x lender_size_bucket.
-- lender_size_bucket = the lender's (LEI) number of action_taken 1-5 applications in that
-- activity_year, counted over the data loaded in the warehouse (one state => volume in that state).
-- Thresholds are a fixed project convention, not a regulatory definition:
--   under_100 | 100_to_999 | 1000_to_9999 | 10000_plus
with apps as (
    select
        activity_year,
        coalesce(state_code, 'unknown') as state_code,
        lei,
        loan_type,
        loan_purpose,
        loan_purpose_desc,
        term_bucket,
        action_taken
    from {{ ref('int_hmda__applications') }}
    where action_taken between 1 and 5
),

lender_volume as (
    select
        activity_year,
        lei,
        count(*) as lender_applications,
        case
            when count(*) < 100   then 'under_100'
            when count(*) < 1000  then '100_to_999'
            when count(*) < 10000 then '1000_to_9999'
            else '10000_plus'
        end as lender_size_bucket
    from apps
    group by 1, 2
),

aggregated as (
    select
        a.activity_year,
        a.state_code,
        a.loan_type,
        a.loan_purpose,
        a.loan_purpose_desc,
        a.term_bucket,
        v.lender_size_bucket,
        count(*)                          as applications,
        countif(a.action_taken = 1)       as originated_loans,
        countif(a.action_taken = 2)       as approved_not_accepted,
        countif(a.action_taken = 3)       as denied_applications,
        countif(a.action_taken = 4)       as withdrawn_applications,
        countif(a.action_taken = 5)       as incomplete_applications,
        countif(a.action_taken in (1, 2)) as approved_applications,
        count(distinct a.lei)             as lenders
    from apps a
    join lender_volume v
      on v.activity_year = a.activity_year
     and v.lei = a.lei
    group by 1, 2, 3, 4, 5, 6, 7
)

select
    array_to_string([
        cast(activity_year as string),
        state_code,
        coalesce(cast(loan_type as string), 'unknown'),
        coalesce(cast(loan_purpose as string), 'unknown'),
        term_bucket,
        lender_size_bucket
    ], '|') as pullthrough_key,
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
    lender_size_bucket,
    lenders,
    applications,
    approved_applications,
    originated_loans,
    approved_not_accepted,
    denied_applications,
    withdrawn_applications,
    incomplete_applications,
    {{ safe_divide('originated_loans', 'applications') }}        as pullthrough_rate,
    {{ safe_divide('originated_loans', 'approved_applications') }} as approved_pullthrough_rate,
    {{ safe_divide('approved_not_accepted', 'applications') }}   as approved_not_accepted_share,
    {{ safe_divide('denied_applications', 'applications') }}     as denied_share,
    {{ safe_divide('withdrawn_applications', 'applications') }}  as withdrawn_share,
    {{ safe_divide('incomplete_applications', 'applications') }} as incomplete_share,
    {{ safe_divide('applications - originated_loans', 'applications') }} as fallout_rate
from aggregated

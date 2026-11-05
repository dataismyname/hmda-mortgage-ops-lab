-- Approval and denial rates. Denominator = decisioned applications
-- (action_taken 1, 2, 3); withdrawn/incomplete are reported separately.
select
    activity_year,
    state_code,
    msa_md,
    loan_purpose_desc,
    loan_product_type,
    count(*)                                         as records,
    countif(is_decisioned)                           as decisioned_applications,
    countif(is_approved)                             as approved_applications,
    countif(is_denied)                               as denied_applications,
    countif(is_originated)                           as originated_loans,
    countif(action_taken in (4, 5))                  as withdrawn_or_incomplete,
    {{ safe_divide('countif(is_approved)', 'countif(is_decisioned)') }} as approval_rate,
    {{ safe_divide('countif(is_denied)', 'countif(is_decisioned)') }}   as denial_rate
from {{ ref('int_hmda__applications') }}
where action_taken between 1 and 5   -- exclude purchased loans and preapprovals
group by 1, 2, 3, 4, 5

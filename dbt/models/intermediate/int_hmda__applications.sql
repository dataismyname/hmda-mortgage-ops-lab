-- Applications enriched with outcome flags and code descriptions.
select
    l.*,
    a.action_taken_desc,
    a.is_decisioned,
    a.is_approved,
    a.is_denied,
    a.is_originated,
    p.loan_purpose_desc,
    case when l.loan_term_months = 360 then '30y'
         when l.loan_term_months = 180 then '15y'
         when l.loan_term_months is null then 'unknown'
         else 'other' end as term_bucket
from {{ ref('stg_hmda__lar') }} l
left join {{ ref('hmda_action_taken') }} a using (action_taken)
left join {{ ref('hmda_loan_purpose') }} p using (loan_purpose)

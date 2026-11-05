-- One row per (denied application, reason). Up to 4 reasons per application;
-- code 10 (not applicable) is excluded.
with denied as (
    select * from {{ ref('int_hmda__applications') }} where is_denied
),
unpivoted as (
    select lar_row_id, activity_year, lei, state_code, msa_md, loan_purpose, reason_rank, denial_reason_code
    from denied,
    unnest([
        struct(1 as reason_rank, denial_reason_1 as denial_reason_code),
        struct(2, denial_reason_2), struct(3, denial_reason_3), struct(4, denial_reason_4)
    ])
)
select u.*, r.denial_reason_desc
from unpivoted u
join {{ ref('hmda_denial_reason') }} r using (denial_reason_code)
where u.denial_reason_code between 1 and 9

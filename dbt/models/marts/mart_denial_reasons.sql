-- Share of denied applications citing each reason (an application can cite up to 4).
with reasons as (
    select activity_year, state_code, msa_md, denial_reason_code, denial_reason_desc,
           count(distinct lar_row_id) as denied_applications_citing
    from {{ ref('int_hmda__denial_reasons') }}
    group by 1, 2, 3, 4, 5
),
denied as (
    select activity_year, state_code, msa_md, countif(is_denied) as denied_applications
    from {{ ref('int_hmda__applications') }}
    group by 1, 2, 3
)
select
    r.*,
    d.denied_applications,
    {{ safe_divide('r.denied_applications_citing', 'd.denied_applications') }} as share_of_denials
from reasons r
join denied d
  on r.activity_year = d.activity_year
 and r.state_code is not distinct from d.state_code
 and r.msa_md is not distinct from d.msa_md

-- Totals per year and outcome must match the source model (action_taken 1-5).
with mart as (
    select activity_year,
           sum(applications)     as applications,
           sum(originated_loans) as originated_loans,
           sum(denied_applications) as denied_applications
    from {{ ref('mart_pipeline_pullthrough') }}
    group by 1
),
source as (
    select activity_year,
           count(*)                    as applications,
           countif(action_taken = 1)   as originated_loans,
           countif(action_taken = 3)   as denied_applications
    from {{ ref('int_hmda__applications') }}
    where action_taken between 1 and 5
    group by 1
)
select coalesce(m.activity_year, s.activity_year) as activity_year,
       m.applications as mart_applications, s.applications as source_applications
from mart m
full outer join source s using (activity_year)
where m.applications is distinct from s.applications
   or m.originated_loans is distinct from s.originated_loans
   or m.denied_applications is distinct from s.denied_applications

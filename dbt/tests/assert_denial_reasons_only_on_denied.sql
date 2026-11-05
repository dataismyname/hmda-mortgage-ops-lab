-- Every unpivoted denial reason must belong to an application with action_taken = 3.
select r.lar_row_id
from {{ ref('int_hmda__denial_reasons') }} r
join {{ ref('int_hmda__applications') }} a using (lar_row_id)
where a.action_taken != 3

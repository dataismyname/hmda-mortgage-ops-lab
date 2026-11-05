-- Approved + denied must equal decisioned applications in every cell.
select *
from {{ ref('mart_approval_denial_rates') }}
where approved_applications + denied_applications != decisioned_applications

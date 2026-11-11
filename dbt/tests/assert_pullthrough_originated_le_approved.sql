-- An originated loan is by definition approved: originated can never exceed approved.
select *
from {{ ref('mart_pipeline_pullthrough') }}
where originated_loans > approved_applications
   or originated_loans + approved_not_accepted != approved_applications

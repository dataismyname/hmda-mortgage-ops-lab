-- Pull-through + the four fallout shares cover every application (tolerance 1e-6,
-- because each NUMERIC division is rounded to 9 decimal places).
select *
from {{ ref('mart_pipeline_pullthrough') }}
where abs(
        pullthrough_rate + approved_not_accepted_share + denied_share
      + withdrawn_share + incomplete_share - 1
      ) > 0.000001
   or originated_loans + approved_not_accepted + denied_applications
      + withdrawn_applications + incomplete_applications != applications

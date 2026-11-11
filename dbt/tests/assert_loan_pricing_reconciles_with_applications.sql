-- Every originated loan lands in exactly one pricing cell, and a cell never has more loans
-- with a rate spread than originated loans.
with mart as (
    select activity_year, sum(originated_loans) as originated_loans,
           countif(loans_with_rate_spread > originated_loans) as bad_cells
    from {{ ref('mart_loan_pricing') }}
    group by 1
),
src as (
    select activity_year, count(*) as originated_loans
    from {{ ref('int_hmda__applications') }}
    where action_taken = 1
    group by 1
)
select coalesce(m.activity_year, s.activity_year) as activity_year,
       m.originated_loans as mart_loans, s.originated_loans as source_loans, m.bad_cells
from mart m
full outer join src s using (activity_year)
where m.originated_loans is distinct from s.originated_loans
   or coalesce(m.bad_cells, 0) > 0

-- One row per HMDA public LAR record, typed. HMDA has no public loan id,
-- so lar_row_id is a content hash plus a sequence for exact duplicates.
with src as (
    select * from {{ source('hmda_raw', 'hmda_lar') }}
    where activity_year in ({{ var('hmda_years') | join(', ') }})
),

hashed as (
    select
        src.*,
        to_hex(md5(to_json_string(src))) as _row_hash
    from src
)

select
    concat(_row_hash, '-', cast(row_number() over (partition by _row_hash order by _ingested_at) as string)) as lar_row_id,
    activity_year,
    upper(lei)                                   as lei,
    nullif(derived_msa_md, 'NA')                 as msa_md,
    nullif(state_code, 'NA')                     as state_code,
    nullif(county_code, 'NA')                    as county_code,
    nullif(census_tract, 'NA')                   as census_tract,
    derived_loan_product_type                    as loan_product_type,
    derived_dwelling_category                    as dwelling_category,
    {{ safe_int('action_taken') }}               as action_taken,
    {{ safe_int('loan_type') }}                  as loan_type,
    {{ safe_int('loan_purpose') }}               as loan_purpose,
    {{ safe_int('lien_status') }}                as lien_status,
    {{ safe_int('occupancy_type') }}             as occupancy_type,
    {{ safe_int('preapproval') }}                as preapproval,
    conforming_loan_limit,
    {{ safe_numeric('loan_amount') }}            as loan_amount,
    {{ safe_numeric('property_value') }}         as property_value,
    {{ safe_numeric('income') }}                 as income_thousands,
    debt_to_income_ratio                         as dti_bucket,
    {{ safe_numeric('combined_loan_to_value_ratio') }} as cltv,
    {{ safe_numeric('interest_rate') }}          as interest_rate,
    {{ safe_numeric('rate_spread') }}            as rate_spread,
    {{ safe_numeric('total_loan_costs') }}       as total_loan_costs,
    {{ safe_numeric('origination_charges') }}    as origination_charges,
    {{ safe_int('loan_term') }}                  as loan_term_months,
    {{ safe_int('hoepa_status') }}               as hoepa_status,
    {{ safe_int('denial_reason_1') }}            as denial_reason_1,
    {{ safe_int('denial_reason_2') }}            as denial_reason_2,
    {{ safe_int('denial_reason_3') }}            as denial_reason_3,
    {{ safe_int('denial_reason_4') }}            as denial_reason_4,
    derived_race,
    derived_ethnicity,
    derived_sex,
    applicant_age,
    {{ safe_numeric('tract_minority_population_percent') }} as tract_minority_pct,
    {{ safe_numeric('tract_to_msa_income_percentage') }}    as tract_to_msa_income_pct,
    _ingested_at
from hashed

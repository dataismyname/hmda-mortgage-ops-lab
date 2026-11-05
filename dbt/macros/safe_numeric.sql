{# HMDA uses 'NA' and 'Exempt' as placeholders; anything non-numeric becomes NULL. #}
{% macro safe_numeric(col) -%}
safe_cast(nullif(nullif(trim({{ col }}), 'NA'), 'Exempt') as numeric)
{%- endmacro %}

{% macro safe_int(col) -%}
safe_cast(nullif(nullif(trim({{ col }}), 'NA'), 'Exempt') as int64)
{%- endmacro %}

{% macro safe_divide(num, den) -%}
safe_divide(cast({{ num }} as numeric), nullif(cast({{ den }} as numeric), 0))
{%- endmacro %}

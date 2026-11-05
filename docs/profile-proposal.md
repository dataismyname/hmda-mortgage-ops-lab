# Propuesta de limpieza del perfil de GitHub (dataismyname)

*Preparado el 4 nov 2026 con la vista pública de https://github.com/dataismyname (API pública y página del perfil). Nada se ha cambiado en GitHub.*

## 1. Estado actual (lectura pública)

| Elemento | Hoy |
|---|---|
| Nombre | David A. Tirado A. |
| Bio | "DATA, data and more data." |
| Web / ubicación | dataexpn.com · Remote |
| Seguidores | 0 |
| Profile README | No existe (no hay repo `dataismyname/dataismyname`) |
| Repos públicos | 6 (ningún fork, ninguno archivado) |
| Pines actuales | credit_card_churn_mlproject, data_science_python_projects, golf_analytics_sql_power_bi, real_estate_web_scrapping_analysis |

| Repo | Lenguaje | Último push | Comentario |
|---|---|---|---|
| fraud-detection-mlops | Python | 4 abr 2025 | Fuerte (Kafka, Spark, MLOps). Hoy **no** está pineado. |
| golf_analytics_sql_power_bi | — | 3 abr 2025 | SQL + Power BI: encaja con BI. |
| credit_card_churn_mlproject | Notebook | 28 mar 2025 | ML end-to-end con Docker/Azure. |
| real_estate_web_scrapping_analysis | Notebook | 2 abr 2025 | Tesis de maestría; nombre con typo ("scrapping"). |
| data_science_python_projects | Notebook | 2 abr 2025 | Colección de ejercicios; se ve de estudiante. |
| data_science_portfolio | — | 22 jun 2023 | Solo un README índice, desactualizado; lo reemplaza el profile README. |

## 2. Bio sugerida (máx. 160 caracteres)

> Analytics & data engineer · BigQuery, dbt, Airflow, Power BI · Building HMDA Mortgage Ops Lab with public U.S. mortgage data · dataexpn.com

Alternativa corta: *"Analytics engineer: dbt, BigQuery, Airflow, Power BI. Public mortgage-market lab with HMDA + FRED data."*

## 3. Los 6 repos a pinear (en este orden)

1. **hmda-mortgage-ops-lab** (nuevo; pinear cuando sea público y tenga README + diagrama).
2. **fraud-detection-mlops** — el más técnico de los actuales.
3. **golf_analytics_sql_power_bi** — prueba de SQL + Power BI.
4. **credit_card_churn_mlproject** — ML end-to-end desplegado.
5. **real_estate_web_scrapping_analysis** — tesis; sugerencia: renombrar a `real-estate-web-scraping-analysis` (GitHub redirige el nombre viejo).
6. **data_science_python_projects** solo como relleno temporal; reemplazarlo por el repo de la fase 2 (tablero) en cuanto exista.

## 4. Archivar u ocultar

| Repo | Acción | Por qué |
|---|---|---|
| data_science_portfolio | Archivar (o volver privado) | Índice de 2023; el profile README cumple esa función. |
| data_science_python_projects | Quitar del pin al publicar la fase 2; archivar después | Ejercicios de curso, diluyen el perfil senior. |
| Cualquier repo de clientes o de producto | Mantener privado | El Lab no debe enlazar ni mencionar código privado. |

Antes de publicar: revisar que ningún repo público tenga llaves, contraseñas o dumps (buscar `password`, `.env`, `key` en el historial).

## 5. Borrador del profile README (repo `dataismyname/dataismyname`)

```markdown
# Hi, I'm David 👋

Analytics & data engineer. I turn messy public and business data into tested
warehouse models, pipelines and dashboards.

**Now building:** [HMDA Mortgage Ops Lab](https://github.com/dataismyname/hmda-mortgage-ops-lab) —
25 M+ U.S. mortgage applications (CFPB HMDA 2024-2025) and FRED rates in BigQuery,
modeled and tested with dbt, orchestrated with Airflow, served in Power BI and Looker Studio.

### Stack
SQL · Python · dbt · BigQuery · Airflow · Power BI · Looker Studio · Spark · Docker

### Selected projects
| Project | What it shows |
|---|---|
| [hmda-mortgage-ops-lab](https://github.com/dataismyname/hmda-mortgage-ops-lab) | Ingestion, dbt models + 50 tests, mortgage market metrics |
| [fraud-detection-mlops](https://github.com/dataismyname/fraud-detection-mlops) | Streaming ML pipeline with Kafka, Spark and MLOps |
| [golf_analytics_sql_power_bi](https://github.com/dataismyname/golf_analytics_sql_power_bi) | SQL modeling and a Power BI report |
| [credit_card_churn_mlproject](https://github.com/dataismyname/credit_card_churn_mlproject) | End-to-end churn model, Docker, Azure |
| [real_estate_web_scrapping_analysis](https://github.com/dataismyname/real_estate_web_scrapping_analysis) | Web scraping, clustering and pricing models |

### Contact
[dataexpn.com](https://dataexpn.com) · LinkedIn: <add link>
```

## 6. Qué necesito de David

- Aprobar o ajustar la bio y el profile README; añadir el enlace de LinkedIn.
- Confirmar si `data_science_portfolio` se archiva o se vuelve privado.
- Confirmar el renombre del repo de real estate.

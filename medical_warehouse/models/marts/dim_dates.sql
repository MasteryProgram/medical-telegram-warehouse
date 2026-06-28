-- Date dimension generated from the range of message dates in the dataset.

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2024-01-01' as date)",
        end_date="cast(current_date + interval '1 year' as date)"
    ) }}
),

final as (
    select
        to_char(date_day, 'YYYYMMDD')::integer  as date_key,
        date_day                                 as full_date,
        extract(dow from date_day)               as day_of_week,
        to_char(date_day, 'Day')                 as day_name,
        extract(week from date_day)              as week_of_year,
        extract(month from date_day)             as month,
        to_char(date_day, 'Month')               as month_name,
        extract(quarter from date_day)           as quarter,
        extract(year from date_day)              as year,
        case when extract(dow from date_day) in (0, 6) then true else false end as is_weekend
    from date_spine
)

select * from final
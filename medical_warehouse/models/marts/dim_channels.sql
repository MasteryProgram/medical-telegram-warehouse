-- One row per channel. Includes aggregate stats across all messages.

with base as (
    select * from {{ ref('stg_telegram_messages') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['channel_name']) }}  as channel_key,
    channel_name,
    channel_title,

    -- Classify channel type based on name
    case
        when lower(channel_name) like '%pharma%'    then 'Pharmaceutical'
        when lower(channel_name) like '%cosmet%'
          or lower(channel_name) like '%lobelia%'   then 'Cosmetics'
        when lower(channel_name) like '%med%'
          or lower(channel_name) like '%doctor%'    then 'Medical'
        else 'Other'
    end                                                        as channel_type,

    min(message_date)                                          as first_post_date,
    max(message_date)                                          as last_post_date,
    count(*)                                                   as total_posts,
    round(avg(views), 1)                                       as avg_views

from base
group by channel_name, channel_title
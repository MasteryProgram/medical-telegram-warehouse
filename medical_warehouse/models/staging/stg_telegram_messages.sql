-- Cleans and standardizes raw Telegram messages.
-- Casts types, renames columns, removes nulls, adds calculated fields.

with source as (
    select * from {{ source('raw', 'telegram_messages') }}
),

cleaned as (
    select
        message_id,
        channel_name,
        channel_title,

        -- Cast date string to proper timestamp
        cast(message_date as timestamp with time zone)  as message_date,

        -- Clean text
        trim(message_text)                              as message_text,

        -- Calculated fields
        length(trim(coalesce(message_text, '')))        as message_length,
        has_media                                       as has_image,
        image_path,

        -- Ensure non-negative counts
        greatest(coalesce(views, 0), 0)                as views,
        greatest(coalesce(forwards, 0), 0)             as forwards

    from source
    where
        message_text is not null
        and trim(message_text) != ''
        and message_id is not null
)

select * from cleaned
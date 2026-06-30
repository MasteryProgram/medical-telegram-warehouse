with detections as (
    select * from {{ source('raw', 'yolo_detections') }}
),
messages as (
    select * from {{ ref('fct_messages') }}
)

select
    detections.message_id,
    messages.channel_key,
    messages.date_key,
    detections.detected_class,
    detections.confidence,
    detections.image_category
from detections
left join messages on detections.message_id = messages.message_id

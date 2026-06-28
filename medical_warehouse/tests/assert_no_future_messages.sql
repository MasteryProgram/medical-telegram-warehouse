-- Custom test: no message should have a date in the future.
-- Returns 0 rows = test passes.

select *
from {{ ref('stg_telegram_messages') }}
where message_date > current_timestamp
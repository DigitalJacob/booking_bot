ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS master_notify_message_id BIGINT;

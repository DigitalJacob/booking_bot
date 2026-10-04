ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS client_evening_reminded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS client_hour_reminded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS master_evening_reminded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS master_hour_reminded_at TIMESTAMPTZ;

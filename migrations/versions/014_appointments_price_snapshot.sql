ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS price_snapshot NUMERIC(10, 2);

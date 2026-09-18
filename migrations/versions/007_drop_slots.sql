DROP INDEX IF EXISTS idx_appointments_active_slot;

ALTER TABLE appointments
    DROP COLUMN IF EXISTS slot_id;

DROP TABLE IF EXISTS slots;

ALTER TABLE appointments
    ALTER COLUMN slot_id DROP NOT NULL;

DROP INDEX IF EXISTS idx_appointments_active_slot;

CREATE UNIQUE INDEX idx_appointments_active_slot
    ON appointments(slot_id)
    WHERE status IN ('pending', 'confirmed')
        AND slot_id IS NOT NULL;

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS rescheduled_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS appointment_reschedules (
    id SERIAL PRIMARY KEY,
    appointment_id INT NOT NULL
        REFERENCES appointments(id) ON DELETE CASCADE,
    actor_user_id BIGINT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('move', 'shift')),
    old_starts_at TIMESTAMPTZ NOT NULL,
    old_ends_at TIMESTAMPTZ NOT NULL,
    new_starts_at TIMESTAMPTZ NOT NULL,
    new_ends_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointment_reschedules_appointment
    ON appointment_reschedules (appointment_id, created_at);

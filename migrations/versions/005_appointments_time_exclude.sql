CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE appointments
    ADD COLUMN starts_at TIMESTAMPTZ,
    ADD COLUMN ends_at TIMESTAMPTZ;

UPDATE appointments AS a
SET
    starts_at = s.starts_at,
    ends_at = s.ends_at
FROM slots AS s
WHERE a.slot_id = s.id;

ALTER TABLE appointments
    ALTER COLUMN starts_at SET NOT NULL,
    ALTER COLUMN ends_at SET NOT NULL;

ALTER TABLE appointments
    ADD CONSTRAINT appointments_ends_after_starts
        CHECK (ends_at > starts_at);

ALTER TABLE appointments
    ADD CONSTRAINT appointments_no_overlap
    EXCLUDE USING gist (
        master_user_id WITH =,
        tstzrange(starts_at, ends_at, '[)') WITH &&
    ) WHERE (status IN ('pending', 'confirmed'));

CREATE INDEX idx_appointments_master_starts
    ON appointments (master_user_id, starts_at);

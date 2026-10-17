CREATE TABLE manual_clients (
    id SERIAL PRIMARY KEY,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    phone_digits VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (master_user_id, phone_digits)
);

CREATE INDEX idx_manual_clients_master_name
    ON manual_clients (master_user_id, name);

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS manual_client_id INT
        REFERENCES manual_clients(id) ON DELETE RESTRICT;

ALTER TABLE appointments
    ALTER COLUMN client_user_id DROP NOT NULL;

ALTER TABLE appointments
    ADD CONSTRAINT appointments_client_xor
        CHECK (num_nonnulls(client_user_id, manual_client_id) = 1);

CREATE INDEX idx_appointments_manual_client_id
    ON appointments (manual_client_id)
    WHERE manual_client_id IS NOT NULL;

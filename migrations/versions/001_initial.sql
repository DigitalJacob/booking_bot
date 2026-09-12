CREATE TABLE users(
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(50),
    language VARCHAR(10) NOT NULL,
    role VARCHAR(30) NOT NULL,
    banned BOOLEAN NOT NULL DEFAULT FALSE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE services(
    id SERIAL PRIMARY KEY,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
    price NUMERIC(10, 2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE slots(
    id SERIAL PRIMARY KEY,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at > starts_at),
    UNIQUE (master_user_id, starts_at)
);

CREATE TABLE appointments(
    id SERIAL PRIMARY KEY,
    client_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    service_id INT NOT NULL
        REFERENCES services(id) ON DELETE RESTRICT,
    slot_id INT NOT NULL
        REFERENCES slots(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('pending', 'confirmed', 'cancelled'))
);

CREATE UNIQUE INDEX idx_appointments_active_slot
    ON appointments(slot_id)
    WHERE status IN ('pending', 'confirmed');

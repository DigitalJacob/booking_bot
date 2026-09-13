CREATE TABLE time_off (
    id SERIAL PRIMARY KEY,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    note VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at > starts_at)
);

CREATE INDEX idx_time_off_master_range
    ON time_off (master_user_id, starts_at, ends_at);

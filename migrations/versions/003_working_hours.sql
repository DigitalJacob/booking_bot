CREATE TABLE working_hours (
    id SERIAL PRIMARY KEY,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    weekday SMALLINT NOT NULL
        CHECK (weekday BETWEEN 1 AND 7),
    starts_time TIME NOT NULL,
    ends_time TIME NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_time > starts_time)
);

CREATE INDEX idx_working_hours_master_weekday
    ON working_hours (master_user_id, weekday);

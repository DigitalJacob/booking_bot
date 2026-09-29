CREATE TABLE work_dates (
    id SERIAL PRIMARY KEY,
    master_user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    work_date DATE NOT NULL,
    starts_time TIME NOT NULL,
    ends_time TIME NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_time > starts_time),
    UNIQUE (master_user_id, work_date)
);

CREATE INDEX idx_work_dates_master_date
    ON work_dates (master_user_id, work_date);

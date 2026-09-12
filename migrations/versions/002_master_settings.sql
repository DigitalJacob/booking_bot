CREATE TABLE master_settings (
    master_user_id BIGINT PRIMARY KEY
        REFERENCES users(user_id) ON DELETE CASCADE,
    timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
    slot_step_minutes INT
        CHECK (slot_step_minutes IS NULL OR slot_step_minutes > 0),
    gap_minutes INT NOT NULL DEFAULT 0
        CHECK (gap_minutes >= 0),
    min_lead_minutes INT NOT NULL DEFAULT 0
        CHECK (min_lead_minutes >= 0),
    booking_horizon_days INT NOT NULL DEFAULT 30
        CHECK (booking_horizon_days > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO master_settings (master_user_id)
SELECT user_id FROM users WHERE role = 'master'
ON CONFLICT (master_user_id) DO NOTHING;

ALTER TABLE master_settings
    ALTER COLUMN booking_horizon_days SET DEFAULT 180;

UPDATE master_settings
SET booking_horizon_days = 180
WHERE booking_horizon_days = 30;

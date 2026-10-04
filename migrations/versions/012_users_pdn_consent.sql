ALTER TABLE users
    ADD COLUMN IF NOT EXISTS pdn_consent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS pdn_consent_version TEXT;

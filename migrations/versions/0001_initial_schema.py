"""Schema v3 — Part 3 of the plan (core) + domain tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-15

Principles (from the plan): user_id NOT NULL everywhere; provenance/staging; soft delete;
no embedding columns (Phase 3); no RLS (Phase 6); value dedup is service-level, not a unique index.
"""
from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    -- gen_random_uuid() is built into PostgreSQL 13+. pgvector — a separate migration in Phase 3.

    ------------------------------------------------------------------ users + profile
    CREATE TABLE users (
        id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE user_profile (
        user_id       UUID PRIMARY KEY REFERENCES users(id),
        date_of_birth DATE NOT NULL,
        sex           VARCHAR(10) NOT NULL,
        blood_type    VARCHAR(10),
        rh_factor     VARCHAR(10),
        height_cm     NUMERIC,
        emergency_contact TEXT,
        updated_at    TIMESTAMPTZ DEFAULT NOW()
    );

    ------------------------------------------------------------------ marker reference data
    CREATE TABLE observation_types (
        id             SERIAL PRIMARY KEY,
        code           VARCHAR(80) UNIQUE NOT NULL,
        loinc_code     VARCHAR(20),
        name_uk        VARCHAR(200) NOT NULL,
        name_en        VARCHAR(200),
        category       VARCHAR(40) NOT NULL,
        specimen       VARCHAR(30),
        value_kind     VARCHAR(20) NOT NULL,
        canonical_unit VARCHAR(40),
        molar_mass     NUMERIC
    );
    CREATE INDEX idx_obstypes_loinc ON observation_types (loinc_code);

    CREATE TABLE observation_synonyms (
        id            SERIAL PRIMARY KEY,
        type_id       INT NOT NULL REFERENCES observation_types(id),
        synonym       VARCHAR(200) NOT NULL,
        lang          VARCHAR(5),
        origin        VARCHAR(10) NOT NULL DEFAULT 'seed',
        learned_from  UUID,
        user_id       UUID,
        created_at    TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE UNIQUE INDEX uq_syn_type_lower ON observation_synonyms (type_id, lower(synonym));
    CREATE INDEX idx_syn_lower ON observation_synonyms (lower(synonym));

    CREATE TABLE unit_conversions (
        id         SERIAL PRIMARY KEY,
        type_id    INT REFERENCES observation_types(id),
        from_unit  VARCHAR(40) NOT NULL,
        to_unit    VARCHAR(40) NOT NULL,
        factor     NUMERIC NOT NULL,
        add_offset NUMERIC DEFAULT 0
    );
    CREATE UNIQUE INDEX uq_unit_conv ON unit_conversions (COALESCE(type_id, 0), from_unit, to_unit);

    CREATE TABLE reference_ranges (
        id          SERIAL PRIMARY KEY,
        type_id     INT NOT NULL REFERENCES observation_types(id),
        sex         VARCHAR(10),
        age_min     INT, age_max INT,
        condition   VARCHAR(40),
        unit        VARCHAR(40) NOT NULL,
        range_kind  VARCHAR(20) NOT NULL DEFAULT 'population',
        range_min   NUMERIC, range_max NUMERIC,
        optimal_min NUMERIC, optimal_max NUMERIC,
        source      VARCHAR(150) NOT NULL
    );
    CREATE INDEX idx_refrange_type ON reference_ranges (type_id);

    ------------------------------------------------------------------ documents
    CREATE TABLE documents (
        id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id        UUID NOT NULL REFERENCES users(id),
        document_date  DATE,
        doc_type       VARCHAR(60),
        title          VARCHAR(300),
        file_path      TEXT NOT NULL,
        file_sha256    CHAR(64) UNIQUE NOT NULL,
        mime_type      VARCHAR(60),
        extracted_text TEXT,
        summary        TEXT,
        deleted_at     TIMESTAMPTZ,
        created_at     TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_documents_user_date ON documents (user_id, document_date DESC);

    ------------------------------------------------------------------ people / facilities
    CREATE TABLE practitioners (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        full_name VARCHAR(200), specialty VARCHAR(100), phone VARCHAR(50), notes TEXT
    );
    CREATE TABLE facilities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        name VARCHAR(200), kind VARCHAR(50), city VARCHAR(100)
    );

    ------------------------------------------------------------------ provenance / staging / audit
    CREATE TABLE ingestion_sources (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(id),
        channel         VARCHAR(30) NOT NULL,
        document_id     UUID REFERENCES documents(id),
        extracted_by    VARCHAR(60),
        prompt_version  VARCHAR(40),
        confidence      NUMERIC(3,2),
        raw_payload     JSONB,
        pipeline_status VARCHAR(20) NOT NULL DEFAULT 'received',
        review_status   VARCHAR(20) NOT NULL DEFAULT 'pending',
        reviewed_by     VARCHAR(60),
        reviewed_at     TIMESTAMPTZ,
        corrected_fields JSONB,
        created_at      TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_ingest_pending ON ingestion_sources (user_id, review_status)
        WHERE review_status = 'pending';

    CREATE TABLE audit_log (
        id BIGSERIAL PRIMARY KEY, at TIMESTAMPTZ DEFAULT NOW(),
        user_id UUID NOT NULL REFERENCES users(id),
        actor VARCHAR(60), action VARCHAR(20), table_name VARCHAR(60), row_id UUID, diff JSONB
    );

    ------------------------------------------------------------------ panels + observations
    CREATE TABLE panels (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID NOT NULL REFERENCES users(id),
        panel_date  DATE NOT NULL,
        panel_type  VARCHAR(200),
        facility_id UUID REFERENCES facilities(id),
        document_id UUID REFERENCES documents(id),
        source_id   UUID REFERENCES ingestion_sources(id),
        row_count_in_document INT,
        rows_extracted        INT
    );

    CREATE TABLE observations (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id       UUID NOT NULL REFERENCES users(id),
        type_id       INT NOT NULL REFERENCES observation_types(id),
        effective_at  TIMESTAMPTZ NOT NULL,
        time_precision VARCHAR(10) NOT NULL DEFAULT 'datetime',
        value_type    VARCHAR(12) NOT NULL DEFAULT 'numeric',
        value_numeric NUMERIC,
        comparator    VARCHAR(2) CHECK (comparator IN ('<','>','<=','>=')),
        value_text    TEXT,
        unit          VARCHAR(40),
        value_canonical NUMERIC,
        ref_min NUMERIC, ref_max NUMERIC,
        status        VARCHAR(20),
        result_status VARCHAR(20) NOT NULL DEFAULT 'final',
        review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
        context       VARCHAR(60),
        group_id      UUID,
        panel_id      UUID REFERENCES panels(id) ON DELETE SET NULL,
        source_id     UUID NOT NULL REFERENCES ingestion_sources(id),
        notes         TEXT,
        deleted_at    TIMESTAMPTZ,
        created_at    TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT chk_has_value CHECK (value_numeric IS NOT NULL OR value_text IS NOT NULL)
    );
    CREATE INDEX idx_obs_main ON observations (user_id, type_id, effective_at DESC)
        WHERE review_status = 'approved' AND deleted_at IS NULL;
    CREATE INDEX idx_obs_source ON observations (source_id);
    CREATE INDEX idx_obs_panel ON observations (panel_id);
    CREATE UNIQUE INDEX uq_obs_in_panel ON observations (panel_id, type_id)
        WHERE panel_id IS NOT NULL AND deleted_at IS NULL;

    ------------------------------------------------------------------ observations change history (trigger)
    CREATE TABLE observation_history (
        id             BIGSERIAL PRIMARY KEY,
        observation_id UUID NOT NULL REFERENCES observations(id),
        changed_at     TIMESTAMPTZ DEFAULT NOW(),
        changed_by     VARCHAR(60),
        reason         VARCHAR(40),
        old_row        JSONB NOT NULL
    );

    CREATE OR REPLACE FUNCTION log_observation_change() RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO observation_history (observation_id, changed_by, reason, old_row)
        VALUES (OLD.id, current_setting('app.actor', true), current_setting('app.reason', true),
                to_jsonb(OLD));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_observation_history
        AFTER UPDATE ON observations
        FOR EACH ROW EXECUTE FUNCTION log_observation_change();

    ------------------------------------------------------------------ diagnoses (two status axes)
    CREATE TABLE diagnoses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        diagnosed_at DATE NOT NULL,
        diagnosis_name VARCHAR(300) NOT NULL,
        icd10_code VARCHAR(10),
        clinical_status     VARCHAR(20),
        verification_status VARCHAR(20),
        severity VARCHAR(50),
        practitioner_id UUID REFERENCES practitioners(id),
        resolved_at DATE,
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_diag_active ON diagnoses (user_id)
        WHERE clinical_status = 'active' AND deleted_at IS NULL;

    ------------------------------------------------------------------ medications
    CREATE TABLE medications (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        medication_name VARCHAR(200) NOT NULL,
        product_type   VARCHAR(20) NOT NULL DEFAULT 'prescription',
        dose_amount    NUMERIC, dose_unit VARCHAR(20), route VARCHAR(30),
        times_per_day  NUMERIC, max_daily_mg NUMERIC,
        dosing_pattern VARCHAR(20),
        schedule       JSONB,
        atc_code       VARCHAR(10),
        start_date DATE NOT NULL, end_date DATE,
        status VARCHAR(20) NOT NULL DEFAULT 'taking',
        prescribed_for VARCHAR(300),
        practitioner_id UUID REFERENCES practitioners(id),
        side_effects TEXT, stop_reason TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_meds_active ON medications (user_id)
        WHERE status = 'taking' AND deleted_at IS NULL;

    CREATE TABLE medication_ingredients (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        medication_id UUID NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
        inn_name      VARCHAR(150) NOT NULL,
        strength      NUMERIC, unit VARCHAR(20)
    );

    CREATE TABLE medication_intakes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id       UUID NOT NULL REFERENCES users(id),
        medication_id UUID NOT NULL REFERENCES medications(id) ON DELETE CASCADE,
        taken_at TIMESTAMPTZ NOT NULL, skipped BOOLEAN DEFAULT FALSE, notes TEXT
    );

    ------------------------------------------------------------------ allergies (fail-safe)
    CREATE TABLE allergies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        allergen VARCHAR(200) NOT NULL,
        allergen_type VARCHAR(30),
        reaction TEXT, severity VARCHAR(20),
        verified BOOLEAN DEFAULT FALSE,
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    ------------------------------------------------------------------ domain tables (Phase 2+, schema ready)
    CREATE TABLE procedures (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        procedure_date DATE NOT NULL,
        procedure_name VARCHAR(300),
        procedure_type VARCHAR(100),
        indication TEXT,
        practitioner_id UUID REFERENCES practitioners(id),
        facility_id UUID REFERENCES facilities(id),
        outcome VARCHAR(100), complications TEXT, recovery_notes TEXT,
        document_id UUID REFERENCES documents(id),
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE vaccinations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        vaccination_date DATE NOT NULL,
        vaccine_name VARCHAR(200), disease VARCHAR(200),
        dose_number INT, batch_number VARCHAR(100),
        practitioner_id UUID REFERENCES practitioners(id),
        facility_id UUID REFERENCES facilities(id),
        reaction TEXT, next_dose_date DATE,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE doctor_visits (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        visit_date DATE NOT NULL,
        practitioner_id UUID REFERENCES practitioners(id),
        facility_id UUID REFERENCES facilities(id),
        reason_for_visit TEXT, complaints TEXT, examination_notes TEXT,
        recommendations TEXT, next_visit_date DATE,
        document_id UUID REFERENCES documents(id),
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE hospital_stays (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        admission_date DATE NOT NULL, discharge_date DATE,
        facility_id UUID REFERENCES facilities(id),
        department VARCHAR(100),
        admission_diagnosis VARCHAR(300), discharge_diagnosis VARCHAR(300),
        treatment_summary TEXT, complications TEXT, discharge_recommendations TEXT,
        document_id UUID REFERENCES documents(id),
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE menstrual_cycles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        start_date DATE NOT NULL, end_date DATE,
        cycle_length_days INT, flow VARCHAR(50), symptoms TEXT[],
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE family_history (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        relation VARCHAR(50),
        degree VARCHAR(10),
        condition VARCHAR(200),
        age_at_diagnosis INT,
        age_at_death INT, cause_of_death VARCHAR(200),
        premature_cvd BOOLEAN,
        status VARCHAR(50),
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE habits (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        habit_type VARCHAR(50),
        status VARCHAR(50),
        cigarettes_per_day INT, smoking_years INT,
        drinks_per_week NUMERIC,
        start_date DATE, end_date DATE,
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE exposures (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        exposure_type VARCHAR(30),
        period_start DATE, period_end DATE,
        intensity VARCHAR(50), notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE implants_devices (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        device_type VARCHAR(100),
        implanted_at DATE,
        mri_contraindicated BOOLEAN,
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE genetic_variants (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        gene VARCHAR(50), variant VARCHAR(200),
        zygosity VARCHAR(20),
        interpretation TEXT,
        interpreted_at DATE,
        interpretation_source VARCHAR(120),
        notes TEXT,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE physical_activities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id),
        activity_date TIMESTAMPTZ NOT NULL,
        activity_type VARCHAR(100), duration_minutes INT, intensity VARCHAR(50),
        distance_km NUMERIC(6,2), calories INT, avg_heart_rate INT, max_heart_rate INT,
        notes TEXT, external_id VARCHAR(200), raw_data JSONB,
        source_id UUID REFERENCES ingestion_sources(id),
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    ------------------------------------------------------------------ raw streams from trackers (partitioned)
    CREATE TABLE device_samples (
        user_id  UUID NOT NULL,
        type_code VARCHAR(40) NOT NULL,
        ts       TIMESTAMPTZ NOT NULL,
        value    NUMERIC NOT NULL,
        source_id UUID,
        UNIQUE (user_id, type_code, ts, source_id)
    ) PARTITION BY RANGE (ts);
    -- default partition so the first insert doesn't fail before the worker creates monthly ones
    CREATE TABLE device_samples_default PARTITION OF device_samples DEFAULT;

    ------------------------------------------------------------------ critical thresholds (rule-engine, Phase 1)
    CREATE TABLE critical_thresholds (
        id SERIAL PRIMARY KEY,
        type_id INT NOT NULL REFERENCES observation_types(id),
        sex VARCHAR(10),
        unit VARCHAR(40) NOT NULL,
        critical_low  NUMERIC,
        critical_high NUMERIC,
        message_uk TEXT NOT NULL,
        source VARCHAR(150) NOT NULL
    );

    ------------------------------------------------------------------ timeline (VIEW)
    CREATE VIEW health_timeline AS
        SELECT 'diagnosis' AS kind, user_id, id,
               (diagnosed_at::timestamp AT TIME ZONE 'UTC') AS at, diagnosis_name AS title
          FROM diagnoses WHERE deleted_at IS NULL
        UNION ALL SELECT 'visit', user_id, id,
               (visit_date::timestamp AT TIME ZONE 'UTC'), reason_for_visit
          FROM doctor_visits WHERE deleted_at IS NULL
        UNION ALL SELECT 'procedure', user_id, id,
               (procedure_date::timestamp AT TIME ZONE 'UTC'), procedure_name
          FROM procedures WHERE deleted_at IS NULL
        UNION ALL SELECT 'panel', user_id, id,
               (panel_date::timestamp AT TIME ZONE 'UTC'), panel_type
          FROM panels
        UNION ALL SELECT 'medication_start', user_id, id,
               (start_date::timestamp AT TIME ZONE 'UTC'), medication_name
          FROM medications WHERE deleted_at IS NULL
        UNION ALL SELECT 'hospital', user_id, id,
               (admission_date::timestamp AT TIME ZONE 'UTC'), admission_diagnosis
          FROM hospital_stays WHERE deleted_at IS NULL
        UNION ALL SELECT 'vaccination', user_id, id,
               (vaccination_date::timestamp AT TIME ZONE 'UTC'), vaccine_name
          FROM vaccinations WHERE deleted_at IS NULL;
    """
    )


def downgrade() -> None:
    op.execute(
        """
    DROP VIEW IF EXISTS health_timeline;
    DROP TABLE IF EXISTS critical_thresholds;
    DROP TABLE IF EXISTS device_samples;
    DROP TABLE IF EXISTS physical_activities;
    DROP TABLE IF EXISTS genetic_variants;
    DROP TABLE IF EXISTS implants_devices;
    DROP TABLE IF EXISTS exposures;
    DROP TABLE IF EXISTS habits;
    DROP TABLE IF EXISTS family_history;
    DROP TABLE IF EXISTS menstrual_cycles;
    DROP TABLE IF EXISTS hospital_stays;
    DROP TABLE IF EXISTS doctor_visits;
    DROP TABLE IF EXISTS vaccinations;
    DROP TABLE IF EXISTS procedures;
    DROP TABLE IF EXISTS allergies;
    DROP TABLE IF EXISTS medication_intakes;
    DROP TABLE IF EXISTS medication_ingredients;
    DROP TABLE IF EXISTS medications;
    DROP TABLE IF EXISTS diagnoses;
    DROP TRIGGER IF EXISTS trg_observation_history ON observations;
    DROP FUNCTION IF EXISTS log_observation_change();
    DROP TABLE IF EXISTS observation_history;
    DROP TABLE IF EXISTS observations;
    DROP TABLE IF EXISTS panels;
    DROP TABLE IF EXISTS audit_log;
    DROP TABLE IF EXISTS ingestion_sources;
    DROP TABLE IF EXISTS facilities;
    DROP TABLE IF EXISTS practitioners;
    DROP TABLE IF EXISTS documents;
    DROP TABLE IF EXISTS reference_ranges;
    DROP TABLE IF EXISTS unit_conversions;
    DROP TABLE IF EXISTS observation_synonyms;
    DROP TABLE IF EXISTS observation_types;
    DROP TABLE IF EXISTS user_profile;
    DROP TABLE IF EXISTS users;
    """
    )

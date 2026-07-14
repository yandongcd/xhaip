# xhaip v1.2 — SQL Schemas (port from haip-0710)

# ──────────────────────────────────────────────
# HIS: Hospital Information System
# ──────────────────────────────────────────────

-- Create schemas
CREATE SCHEMA IF NOT EXISTS his;
CREATE SCHEMA IF NOT EXISTS emr;
CREATE SCHEMA IF NOT EXISTS lis;
CREATE SCHEMA IF NOT EXISTS pacs;
CREATE SCHEMA IF NOT EXISTS nis;

-- Patient Master Index
CREATE TABLE IF NOT EXISTS his.patient_info (
    id              SERIAL PRIMARY KEY,
    patient_id      VARCHAR(20)  NOT NULL UNIQUE,
    mrn             VARCHAR(20)  NOT NULL,
    inpatient_no    VARCHAR(20)  NOT NULL,
    name            VARCHAR(50)  NOT NULL,
    gender          VARCHAR(4),
    age             NUMERIC(5,1),
    ethnicity       VARCHAR(20),
    dept_code       VARCHAR(50)  NOT NULL,
    dept_name       VARCHAR(50)  NOT NULL
);

-- Visit / Admission Record
CREATE TABLE IF NOT EXISTS his.visit_record (
    id                     SERIAL PRIMARY KEY,
    patient_id             VARCHAR(20)  NOT NULL REFERENCES his.patient_info(patient_id),
    admission_date         DATE         NOT NULL,
    discharge_date         DATE,
    admission_type         VARCHAR(20),
    insurance_type         VARCHAR(30),
    bed_no                 VARCHAR(20),
    diet_order             VARCHAR(30),
    attending_physician    VARCHAR(20),
    icd_code               VARCHAR(20),
    billing_category       VARCHAR(10),
    estimated_cost         NUMERIC(12,2)
);
CREATE INDEX IF NOT EXISTS idx_visit_patient ON his.visit_record(patient_id);

-- Registration Record
CREATE TABLE IF NOT EXISTS his.registration (
    id                  SERIAL PRIMARY KEY,
    patient_id          VARCHAR(20) NOT NULL REFERENCES his.patient_info(patient_id),
    registration_date   DATE        NOT NULL,
    dept_name           VARCHAR(50),
    visit_number        VARCHAR(30),
    appointment_type    VARCHAR(20),
    payment_method      VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_reg_patient ON his.registration(patient_id);

-- Diagnosis Record
CREATE TABLE IF NOT EXISTS his.diagnosis (
    id               SERIAL PRIMARY KEY,
    patient_id       VARCHAR(20) NOT NULL REFERENCES his.patient_info(patient_id),
    diagnosis_name   TEXT,
    icd10_code       VARCHAR(20),
    diagnosis_date   DATE,
    diagnosis_type   VARCHAR(20) DEFAULT '入院诊断'
);
CREATE INDEX IF NOT EXISTS idx_diag_patient ON his.diagnosis(patient_id);

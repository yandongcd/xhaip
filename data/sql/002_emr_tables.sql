# EMR: Electronic Medical Record Tables

-- Admission Note
CREATE TABLE IF NOT EXISTS emr.admission_note (
    id                SERIAL PRIMARY KEY,
    patient_id        VARCHAR(20)  NOT NULL,
    admission_date    DATE,
    chief_complaint   TEXT,
    present_illness   TEXT,
    past_history      TEXT,
    allergy_history   TEXT,
    physical_exam     TEXT,
    diagnosis         VARCHAR(200),
    icd10             VARCHAR(20),
    height_cm         NUMERIC(6,1),
    weight_kg         NUMERIC(6,1)
);
CREATE INDEX IF NOT EXISTS idx_adm_note_patient ON emr.admission_note(patient_id);

-- Progress Note
CREATE TABLE IF NOT EXISTS emr.progress_note (
    id           SERIAL PRIMARY KEY,
    patient_id   VARCHAR(20)  NOT NULL,
    note_date    DATE         NOT NULL,
    note_time    VARCHAR(10),
    note_type    VARCHAR(20)  NOT NULL DEFAULT '日常病程记录',
    doctor       VARCHAR(20),
    content      TEXT
);
CREATE INDEX IF NOT EXISTS idx_prog_note_patient ON emr.progress_note(patient_id);
CREATE INDEX IF NOT EXISTS idx_prog_note_date    ON emr.progress_note(patient_id, note_date);

-- Discharge Summary
CREATE TABLE IF NOT EXISTS emr.discharge_summary (
    id                    SERIAL PRIMARY KEY,
    patient_id            VARCHAR(20)  NOT NULL,
    admission_date        DATE,
    discharge_date        DATE,
    admitting_diagnosis   VARCHAR(200),
    discharge_diagnosis   VARCHAR(200),
    treatment_summary     TEXT,
    follow_up_advice      VARCHAR(200),
    doctor                VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_discharge_patient ON emr.discharge_summary(patient_id);

-- Medication Order
CREATE TABLE IF NOT EXISTS emr.medication_order (
    id                SERIAL PRIMARY KEY,
    patient_id        VARCHAR(20)  NOT NULL,
    medication_name   VARCHAR(100) NOT NULL,
    dose              VARCHAR(50),
    route             VARCHAR(20),
    start_date        DATE,
    order_status      VARCHAR(20) DEFAULT '住院医嘱'
);
CREATE INDEX IF NOT EXISTS idx_med_order_patient ON emr.medication_order(patient_id);

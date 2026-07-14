# LIS: Laboratory Information System

-- Lab Order
CREATE TABLE IF NOT EXISTS lis.lab_order (
    id                   SERIAL PRIMARY KEY,
    patient_id           VARCHAR(20) NOT NULL,
    order_date           DATE,
    test_item            VARCHAR(100),
    specimen_type        VARCHAR(50),
    order_status         VARCHAR(20) DEFAULT '已申请',
    ordering_physician   VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_lab_order_patient ON lis.lab_order(patient_id);

-- Lab Result
CREATE TABLE IF NOT EXISTS lis.lab_result (
    id             SERIAL PRIMARY KEY,
    patient_id     VARCHAR(20) NOT NULL,
    test_item      VARCHAR(100) NOT NULL,
    test_result    NUMERIC(10,2),
    unit           VARCHAR(20),
    reference_min  NUMERIC(10,2),
    reference_max  NUMERIC(10,2),
    abnormal_flag  VARCHAR(5),
    result_date    DATE
);
CREATE INDEX IF NOT EXISTS idx_lab_res_patient ON lis.lab_result(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_res_test    ON lis.lab_result(patient_id, test_item);

# PACS: Imaging System

CREATE TABLE IF NOT EXISTS pacs.imaging_exam (
    id           SERIAL PRIMARY KEY,
    patient_id   VARCHAR(20) NOT NULL,
    exam_type    VARCHAR(50),
    body_part    VARCHAR(50),
    exam_date    DATE,
    exam_status  VARCHAR(20) DEFAULT '已登记'
);
CREATE INDEX IF NOT EXISTS idx_img_exam_patient ON pacs.imaging_exam(patient_id);

CREATE TABLE IF NOT EXISTS pacs.imaging_report (
    id              SERIAL PRIMARY KEY,
    patient_id      VARCHAR(20) NOT NULL,
    exam_id         INTEGER REFERENCES pacs.imaging_exam(id),
    report_content  TEXT,
    impression      TEXT,
    radiologist     VARCHAR(20),
    report_date     DATE
);
CREATE INDEX IF NOT EXISTS idx_img_rep_patient ON pacs.imaging_report(patient_id);

# NIS: Nursing Information System

CREATE TABLE IF NOT EXISTS nis.vital_signs (
    id              SERIAL PRIMARY KEY,
    patient_id      VARCHAR(20) NOT NULL,
    record_time     TIMESTAMP,
    temperature     NUMERIC(4,1),
    heart_rate      INTEGER,
    respiratory_rate INTEGER,
    systolic_bp     INTEGER,
    diastolic_bp    INTEGER,
    spo2            INTEGER,
    pain_score      INTEGER,
    nurse_id        VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_vs_patient ON nis.vital_signs(patient_id);

CREATE TABLE IF NOT EXISTS nis.nursing_assessment (
    id                    SERIAL PRIMARY KEY,
    patient_id            VARCHAR(20) NOT NULL,
    assessment_date       DATE,
    fall_risk             VARCHAR(20),
    pressure_ulcer_risk   VARCHAR(20),
    nutrition_risk        VARCHAR(20),
    barthel_index         INTEGER,
    nurse_id              VARCHAR(20)
);
CREATE INDEX IF NOT EXISTS idx_na_patient ON nis.nursing_assessment(patient_id);

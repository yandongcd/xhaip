"""Hospital Data Models — SQLAlchemy ORM models mirroring haip-0710 schema.

Covers: HIS (patient, visit, registration, diagnosis),
        EMR (admission, progress, discharge, medication),
        LIS (lab orders, test results, blood gas, urine),
        PACS (imaging exams, reports),
        NIS (nursing assessments, vital signs)

All models can be created by `database.create_tables()` or Alembic migration.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base model with schema support."""


# ── HIS: Hospital Information System ──


class PatientInfo(Base):
    """患者主索引 — his.patient_info"""

    __tablename__ = "patient_info"
    __table_args__ = {"schema": "his", "comment": "患者主索引"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    mrn: Mapped[str] = mapped_column(String(20), nullable=False)
    inpatient_no: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(4))
    age: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    ethnicity: Mapped[Optional[str]] = mapped_column(String(20))
    dept_code: Mapped[str] = mapped_column(String(50), nullable=False)
    dept_name: Mapped[str] = mapped_column(String(50), nullable=False)


class VisitRecord(Base):
    """就诊记录 — his.visit_record"""

    __tablename__ = "visit_record"
    __table_args__ = (
        Index("idx_visit_patient", "patient_id"),
        {"schema": "his", "comment": "就诊记录"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), ForeignKey("his.patient_info.patient_id"), nullable=False)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    discharge_date: Mapped[Optional[date]] = mapped_column(Date)
    admission_type: Mapped[Optional[str]] = mapped_column(String(20))
    insurance_type: Mapped[Optional[str]] = mapped_column(String(30))
    bed_no: Mapped[Optional[str]] = mapped_column(String(20))
    diet_order: Mapped[Optional[str]] = mapped_column(String(30))
    attending_physician: Mapped[Optional[str]] = mapped_column(String(20))
    icd_code: Mapped[Optional[str]] = mapped_column(String(20))
    billing_category: Mapped[Optional[str]] = mapped_column(String(10))
    estimated_cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))


class Registration(Base):
    """挂号记录 — his.registration"""

    __tablename__ = "registration"
    __table_args__ = (
        Index("idx_reg_patient", "patient_id"),
        {"schema": "his", "comment": "挂号记录"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), ForeignKey("his.patient_info.patient_id"), nullable=False)
    registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    dept_name: Mapped[Optional[str]] = mapped_column(String(50))
    visit_number: Mapped[Optional[str]] = mapped_column(String(30))
    appointment_type: Mapped[Optional[str]] = mapped_column(String(20))
    payment_method: Mapped[Optional[str]] = mapped_column(String(20))


class Diagnosis(Base):
    """诊断记录 — his.diagnosis"""

    __tablename__ = "diagnosis"
    __table_args__ = (
        Index("idx_diag_patient", "patient_id"),
        {"schema": "his", "comment": "诊断记录"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), ForeignKey("his.patient_info.patient_id"), nullable=False)
    diagnosis_name: Mapped[Optional[str]] = mapped_column(Text)
    icd10_code: Mapped[Optional[str]] = mapped_column(String(20))
    diagnosis_date: Mapped[Optional[date]] = mapped_column(Date)
    diagnosis_type: Mapped[str] = mapped_column(String(20), default="入院诊断")


# ── EMR: Electronic Medical Record ──


class AdmissionNote(Base):
    """入院记录 — emr.admission_note"""

    __tablename__ = "admission_note"
    __table_args__ = (
        Index("idx_adm_note_patient", "patient_id"),
        {"schema": "emr", "comment": "入院记录"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    admission_date: Mapped[Optional[date]] = mapped_column(Date)
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text)
    present_illness: Mapped[Optional[str]] = mapped_column(Text)
    past_history: Mapped[Optional[str]] = mapped_column(Text)
    allergy_history: Mapped[Optional[str]] = mapped_column(Text)
    physical_exam: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(200))
    icd10: Mapped[Optional[str]] = mapped_column(String(20))
    height_cm: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))
    weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(6, 1))


class ProgressNote(Base):
    """病程记录 — emr.progress_note"""

    __tablename__ = "progress_note"
    __table_args__ = (
        Index("idx_prog_note_patient", "patient_id"),
        Index("idx_prog_note_date", "patient_id", "note_date"),
        {"schema": "emr", "comment": "病程记录"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    note_date: Mapped[date] = mapped_column(Date, nullable=False)
    note_time: Mapped[Optional[str]] = mapped_column(String(10))
    note_type: Mapped[str] = mapped_column(String(20), nullable=False, default="日常病程记录")
    doctor: Mapped[Optional[str]] = mapped_column(String(20))
    content: Mapped[Optional[str]] = mapped_column(Text)


class DischargeSummary(Base):
    """出院小结 — emr.discharge_summary"""

    __tablename__ = "discharge_summary"
    __table_args__ = (
        Index("idx_discharge_patient", "patient_id"),
        {"schema": "emr", "comment": "出院小结"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    admission_date: Mapped[Optional[date]] = mapped_column(Date)
    discharge_date: Mapped[Optional[date]] = mapped_column(Date)
    admitting_diagnosis: Mapped[Optional[str]] = mapped_column(String(200))
    discharge_diagnosis: Mapped[Optional[str]] = mapped_column(String(200))
    treatment_summary: Mapped[Optional[str]] = mapped_column(Text)
    follow_up_advice: Mapped[Optional[str]] = mapped_column(String(200))
    doctor: Mapped[Optional[str]] = mapped_column(String(20))


class MedicationOrder(Base):
    """医嘱处方 — emr.medication_order"""

    __tablename__ = "medication_order"
    __table_args__ = (
        Index("idx_med_order_patient", "patient_id"),
        {"schema": "emr", "comment": "医嘱处方"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    medication_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dose: Mapped[Optional[str]] = mapped_column(String(50))
    route: Mapped[Optional[str]] = mapped_column(String(20))
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    order_status: Mapped[str] = mapped_column(String(20), default="住院医嘱")


# ── LIS: Laboratory Information System ──


class LabOrder(Base):
    """检验申请 — lis.lab_order"""

    __tablename__ = "lab_order"
    __table_args__ = (
        Index("idx_lab_order_patient", "patient_id"),
        {"schema": "lis", "comment": "检验申请"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    order_date: Mapped[Optional[date]] = mapped_column(Date)
    test_item: Mapped[Optional[str]] = mapped_column(String(100))
    specimen_type: Mapped[Optional[str]] = mapped_column(String(50))
    order_status: Mapped[str] = mapped_column(String(20), default="已申请")
    ordering_physician: Mapped[Optional[str]] = mapped_column(String(20))


class LabResult(Base):
    """检验结果 — lis.lab_result"""

    __tablename__ = "lab_result"
    __table_args__ = (
        Index("idx_lab_res_patient", "patient_id"),
        Index("idx_lab_res_test", "patient_id", "test_item"),
        {"schema": "lis", "comment": "检验结果"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    test_item: Mapped[str] = mapped_column(String(100), nullable=False)
    test_result: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    reference_min: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    reference_max: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    abnormal_flag: Mapped[Optional[str]] = mapped_column(String(5))
    result_date: Mapped[Optional[date]] = mapped_column(Date)


# ── PACS: Imaging ──


class ImagingExam(Base):
    """影像检查 — pacs.imaging_exam"""

    __tablename__ = "imaging_exam"
    __table_args__ = (
        Index("idx_img_exam_patient", "patient_id"),
        {"schema": "pacs", "comment": "影像检查"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    exam_type: Mapped[Optional[str]] = mapped_column(String(50))
    body_part: Mapped[Optional[str]] = mapped_column(String(50))
    exam_date: Mapped[Optional[date]] = mapped_column(Date)
    exam_status: Mapped[str] = mapped_column(String(20), default="已登记")


class ImagingReport(Base):
    """影像报告 — pacs.imaging_report"""

    __tablename__ = "imaging_report"
    __table_args__ = (
        Index("idx_img_rep_patient", "patient_id"),
        {"schema": "pacs", "comment": "影像报告"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    exam_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pacs.imaging_exam.id"))
    report_content: Mapped[Optional[str]] = mapped_column(Text)
    impression: Mapped[Optional[str]] = mapped_column(Text)
    radiologist: Mapped[Optional[str]] = mapped_column(String(20))
    report_date: Mapped[Optional[date]] = mapped_column(Date)


# ── NIS: Nursing Information System ──


class VitalSigns(Base):
    """生命体征 — nis.vital_signs"""

    __tablename__ = "vital_signs"
    __table_args__ = (
        Index("idx_vs_patient", "patient_id"),
        {"schema": "nis", "comment": "生命体征"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    record_time: Mapped[Optional[datetime]] = mapped_column()
    temperature: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer)
    respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer)
    systolic_bp: Mapped[Optional[int]] = mapped_column(Integer)
    diastolic_bp: Mapped[Optional[int]] = mapped_column(Integer)
    spo2: Mapped[Optional[int]] = mapped_column(Integer)
    pain_score: Mapped[Optional[int]] = mapped_column(Integer)
    nurse_id: Mapped[Optional[str]] = mapped_column(String(20))


class NursingAssessment(Base):
    """护理评估 — nis.nursing_assessment"""

    __tablename__ = "nursing_assessment"
    __table_args__ = (
        Index("idx_na_patient", "patient_id"),
        {"schema": "nis", "comment": "护理评估"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False)
    assessment_date: Mapped[Optional[date]] = mapped_column(Date)
    fall_risk: Mapped[Optional[str]] = mapped_column(String(20))
    pressure_ulcer_risk: Mapped[Optional[str]] = mapped_column(String(20))
    nutrition_risk: Mapped[Optional[str]] = mapped_column(String(20))
    barthel_index: Mapped[Optional[int]] = mapped_column(Integer)
    nurse_id: Mapped[Optional[str]] = mapped_column(String(20))


# ── All model tables ──

ALL_MODELS = [
    PatientInfo, VisitRecord, Registration, Diagnosis,
    AdmissionNote, ProgressNote, DischargeSummary, MedicationOrder,
    LabOrder, LabResult,
    ImagingExam, ImagingReport,
    VitalSigns, NursingAssessment,
]

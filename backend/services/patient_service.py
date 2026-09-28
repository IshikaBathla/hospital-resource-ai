from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.patient import Patient


def get_all_patients(db: Session):
    return db.query(Patient).all()


def get_patient_by_id(db: Session, patient_id: str):
    return (
        db.query(Patient)
        .filter(Patient.patient_id == patient_id)
        .first()
    )


def create_patient(db: Session, patient_data):
    waiting_since = (
        datetime.now()
        if patient_data.status.lower() == "waiting"
        else None
    )

    patient = Patient(
        patient_id=patient_data.patient_id,
        name=patient_data.name,
        age=patient_data.age,
        emergency_level=patient_data.emergency_level,
        status=patient_data.status,
        waiting_since=waiting_since
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient
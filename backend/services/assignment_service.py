from sqlalchemy.orm import Session

from backend.models.assignment import Assignment
from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment


def get_all_assignments(db: Session):

    return db.query(Assignment).all()


def get_assignment_by_id(
    db: Session,
    assignment_id: int
):

    return (
        db.query(Assignment)
        .filter(
            Assignment.assignment_id == assignment_id
        )
        .first()
    )


def create_assignment(
    db: Session,
    assignment_data
):

    # -----------------------------
    # Validate patient
    # -----------------------------

    patient = (
        db.query(Patient)
        .filter(
            Patient.patient_id
            == assignment_data.patient_id
        )
        .first()
    )

    if not patient:
        raise ValueError(
            "Patient not found"
        )

    # -----------------------------
    # Validate bed
    # -----------------------------

    bed = None

    if assignment_data.bed_id:

        bed = (
            db.query(Bed)
            .filter(
                Bed.bed_id
                == assignment_data.bed_id
            )
            .first()
        )

        if not bed:
            raise ValueError(
                "Bed not found"
            )

        if bed.status != "available":
            raise ValueError(
                f"Bed {bed.bed_id} is not available"
            )

    # -----------------------------
    # Validate staff
    # -----------------------------

    staff = None

    if assignment_data.staff_id:

        staff = (
            db.query(Staff)
            .filter(
                Staff.staff_id
                == assignment_data.staff_id
            )
            .first()
        )

        if not staff:
            raise ValueError(
                "Staff not found"
            )

        if staff.status != "available":
            raise ValueError(
                f"Staff {staff.staff_id} is not available"
            )

    # -----------------------------
    # Validate equipment
    # -----------------------------

    equipment = None

    if assignment_data.equipment_id:

        equipment = (
            db.query(Equipment)
            .filter(
                Equipment.equipment_id
                == assignment_data.equipment_id
            )
            .first()
        )

        if not equipment:
            raise ValueError(
                "Equipment not found"
            )

        if equipment.status != "available":
            raise ValueError(
                f"Equipment {equipment.equipment_id} "
                "is not available"
            )

    # -----------------------------
    # Create assignment
    # -----------------------------

    assignment = Assignment(
        patient_id=assignment_data.patient_id,
        bed_id=assignment_data.bed_id,
        staff_id=assignment_data.staff_id,
        equipment_id=assignment_data.equipment_id
    )

    db.add(assignment)

    # -----------------------------
    # Update bed state
    # -----------------------------

    if bed:

        bed.status = "occupied"
        bed.patient_id = patient.patient_id
        bed.expected_release_at = None

    # -----------------------------
    # Update patient state
    # -----------------------------

    patient.status = "admitted"

    # -----------------------------
    # Update staff state
    # -----------------------------

    if staff:
        staff.status = "assigned"

    # -----------------------------
    # Update equipment state
    # -----------------------------

    if equipment:
        equipment.status = "assigned"

    db.commit()

    db.refresh(assignment)

    return assignment
def delete_assignment(
    db: Session,
    assignment_id: int
):

    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.assignment_id == assignment_id
        )
        .first()
    )

    if not assignment:
        raise ValueError(
            "Assignment not found"
        )

    db.delete(assignment)

    db.commit()

    return {
        "status": "success",
        "message": "Assignment deleted",
        "assignment_id": assignment_id
    }
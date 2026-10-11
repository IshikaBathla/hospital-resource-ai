import random
from datetime import datetime, timedelta

from backend.database import SessionLocal, initialize_database
from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment


PATIENT_COUNT = 100
BED_COUNT = 60
STAFF_COUNT = 30

# Dedicated random generator for reproducible synthetic data.
rng = random.Random(42)

DEPARTMENTS = [
    "Emergency",
    "Cardiology",
    "Neurology",
    "General Medicine",
    "Respiratory",
]

PRIORITIES = ["critical", "high", "medium", "low"]
PRIORITY_WEIGHTS = [10, 20, 35, 35]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Ishaan",
    "Ananya", "Diya", "Aadhya", "Myra", "Saanvi",
    "Rohan", "Kavya", "Meera", "Reyansh", "Aanya",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Patel",
    "Kumar", "Mehta", "Kapoor", "Malhotra", "Joshi",
]

EQUIPMENT_TYPES = [
    "CT Scanner",
    "MRI Scanner",
    "Ventilator",
    "ECG Machine",
    "Ultrasound",
]

EQUIPMENT_LOCATIONS = [
    "Emergency Department",
    "Radiology",
    "ICU",
    "Cardiology",
    "Diagnostic Centre",
]


def seed_patients(db):
    added = 0

    for i in range(1, PATIENT_COUNT + 1):
        patient_id = f"SYN-P{i:03d}"

        # Never modify an existing record.
        if db.get(Patient, patient_id) is not None:
            continue

        priority = rng.choices(
            PRIORITIES,
            weights=PRIORITY_WEIGHTS,
            k=1,
        )[0]

        waiting_since = datetime.now() - timedelta(
            minutes=rng.randint(5, 360)
        )

        required_equipment = (
            rng.choice(EQUIPMENT_TYPES)
            if priority in ("critical", "high")
            and rng.random() < 0.5
            else None
        )

        patient = Patient(
            patient_id=patient_id,
            name=(
                f"{rng.choice(FIRST_NAMES)} "
                f"{rng.choice(LAST_NAMES)}"
            ),
            age=rng.randint(1, 90),
            emergency_level=priority,
            status="waiting",
            waiting_since=waiting_since,
            required_equipment_type=required_equipment,
            care_status="active",
            transfer_ready=False,
            expected_release_at=None,
            staff_note="Synthetic demo record; not real patient data.",
        )

        db.add(patient)
        added += 1

    db.flush()
    print(f"Patients added: {added}")


def seed_beds(db):
    added = 0

    for i in range(1, BED_COUNT + 1):
        bed_id = f"SYN-B{i:03d}"

        # Never modify an existing record.
        if db.get(Bed, bed_id) is not None:
            continue

        # 30 ICU beds and 30 General beds.
        # Critical/high patients require ICU in the optimizer.
        ward = "ICU" if i <= 30 else "General"

        # Keep demo beds available for optimization testing.
        # Do not create incorrect patient-bed relationships.
        bed = Bed(
            bed_id=bed_id,
            ward=ward,
            status="available",
            patient_id=None,
            expected_release_at=None,
        )

        db.add(bed)
        added += 1

    db.flush()
    print(f"Beds added: {added}")


def seed_staff(db):
    added = 0

    roles = ["Doctor", "Nurse", "Technician"]
    role_weights = [30, 55, 15]

    for i in range(1, STAFF_COUNT + 1):
        staff_id = f"SYN-S{i:03d}"

        # Never modify an existing record.
        if db.get(Staff, staff_id) is not None:
            continue

        role = rng.choices(
            roles,
            weights=role_weights,
            k=1,
        )[0]

        staff = Staff(
            staff_id=staff_id,
            name=(
                f"{rng.choice(FIRST_NAMES)} "
                f"{rng.choice(LAST_NAMES)}"
            ),
            role=role,
            department=rng.choice(DEPARTMENTS),
            status="available",
        )

        db.add(staff)
        added += 1

    db.flush()
    print(f"Staff added: {added}")


def seed_equipment(db):
    added = 0

    # Three units of each equipment type: 15 total.
    for equipment_type in EQUIPMENT_TYPES:
        prefix = equipment_type.split()[0][:3].upper()

        for unit in range(1, 4):
            equipment_id = f"SYN-{prefix}-{unit:02d}"

            # Never modify an existing record.
            if db.get(Equipment, equipment_id) is not None:
                continue

            equipment = Equipment(
                equipment_id=equipment_id,
                equipment_type=equipment_type,
                status="available",
                location=rng.choice(EQUIPMENT_LOCATIONS),
            )

            db.add(equipment)
            added += 1

    db.flush()
    print(f"Equipment units added: {added}")


def main():
    # Uses the project's existing database initialization.
    initialize_database()

    db = SessionLocal()

    try:
        seed_patients(db)
        seed_beds(db)
        seed_staff(db)
        seed_equipment(db)

        db.commit()

        print("\nSynthetic hospital data seeding completed.")
        print("Generated IDs use the SYN- prefix.")
        print("Existing records were not intentionally modified.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
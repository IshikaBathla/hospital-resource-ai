from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.bed import Bed


# =========================================================
# CREATE PROCEDURE
# =========================================================

def create_procedure(
    db: Session,
    procedure_data
):

    # -----------------------------------------
    # Validate bed if provided
    # -----------------------------------------

    bed = None

    if procedure_data.bed_id:

        bed = (
            db.query(Bed)
            .filter(
                Bed.bed_id
                == procedure_data.bed_id
            )
            .first()
        )

        if not bed:

            raise ValueError(
                "Bed not found"
            )

        if bed.status != "occupied":

            raise ValueError(
                "Procedure can only be started "
                "on an occupied bed"
            )

    # -----------------------------------------
    # Calculate expected end time
    # -----------------------------------------

    now = datetime.now()

    expected_end_at = (
        now
        + timedelta(
            minutes=procedure_data.duration_minutes
        )
    )

    # -----------------------------------------
    # Insert procedure
    # -----------------------------------------

    result = db.execute(
        text("""
            INSERT INTO procedures
            (
                patient_id,
                bed_id,
                procedure_name,
                status,
                expected_end_at
            )
            VALUES
            (
                :patient_id,
                :bed_id,
                :procedure_name,
                'in_progress',
                :expected_end_at
            )
            RETURNING
                procedure_id,
                patient_id,
                bed_id,
                procedure_name,
                status,
                expected_end_at
        """),
        {
            "patient_id":
                procedure_data.patient_id,

            "bed_id":
                procedure_data.bed_id,

            "procedure_name":
                procedure_data.procedure_name,

            "expected_end_at":
                expected_end_at
        }
    )

    procedure = result.mappings().first()

    # -----------------------------------------
    # Update bed release time
    # -----------------------------------------

    if bed:

        bed.expected_release_at = (
            expected_end_at
        )

    db.commit()

    return procedure


# =========================================================
# GET ALL PROCEDURES
# =========================================================

def get_all_procedures(
    db: Session
):

    result = db.execute(
        text("""
            SELECT
                procedure_id,
                patient_id,
                bed_id,
                procedure_name,
                status,
                expected_end_at
            FROM procedures
            ORDER BY procedure_id DESC
        """)
    ).mappings().all()

    return [
        dict(procedure)
        for procedure in result
    ]


# =========================================================
# GET PROCEDURE BY ID
# =========================================================

def get_procedure_by_id(
    db: Session,
    procedure_id: int
):

    result = db.execute(
        text("""
            SELECT
                procedure_id,
                patient_id,
                bed_id,
                procedure_name,
                status,
                expected_end_at
            FROM procedures
            WHERE procedure_id = :procedure_id
        """),
        {
            "procedure_id":
                procedure_id
        }
    ).mappings().first()

    if not result:
        return None

    return dict(result)


# =========================================================
# AUTOMATICALLY COMPLETE EXPIRED PROCEDURES
# =========================================================

def refresh_expired_procedures(
    db: Session
):

    now = datetime.now()

    expired_procedures = db.execute(
        text("""
            SELECT
                procedure_id,
                patient_id,
                bed_id
            FROM procedures
            WHERE status = 'in_progress'
              AND expected_end_at IS NOT NULL
              AND expected_end_at <= :now
        """),
        {
            "now": now
        }
    ).mappings().all()

    released_beds = []

    for procedure in expired_procedures:

        # -----------------------------------------
        # Procedure → completed
        # -----------------------------------------

        db.execute(
            text("""
                UPDATE procedures
                SET status = 'completed'
                WHERE procedure_id = :procedure_id
            """),
            {
                "procedure_id":
                    procedure["procedure_id"]
            }
        )

        # -----------------------------------------
        # Bed → available
        # -----------------------------------------

        if procedure["bed_id"]:

            bed = (
                db.query(Bed)
                .filter(
                    Bed.bed_id
                    == procedure["bed_id"]
                )
                .first()
            )

            if bed:

                bed.status = "available"

                bed.patient_id = None

                bed.expected_release_at = None

                released_beds.append(
                    bed.bed_id
                )

    db.commit()

    return {
        "completed_procedures":
            len(expired_procedures),

        "released_beds":
            released_beds
    }
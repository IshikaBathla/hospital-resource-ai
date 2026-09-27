from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.patient import Patient
from backend.models.bed import Bed
from backend.models.staff import Staff
from backend.models.equipment import Equipment

from backend.services.constraint_service import can_reallocate_patient

from backend.schemas.candidate import RecommendationCandidate


# =========================================================
# SIMULATION STATE
# =========================================================

def get_simulation_state(db: Session):
    """
    Read the current hospital state.

    IMPORTANT:
    This function only reads the real database.
    It NEVER modifies the real database.
    """

    return {
        "patients": db.query(Patient).all(),
        "beds": db.query(Bed).all(),
        "staff": db.query(Staff).all(),
        "equipment": db.query(Equipment).all()
    }


# =========================================================
# BED HELPERS
# =========================================================

def find_available_bed(
    beds,
    emergency_level: str,
    required_ward: str | None
):
    """
    Find an immediately available suitable bed.
    """

    level = emergency_level.lower()

    candidate_beds = [
        bed
        for bed in beds
        if bed.status == "available"
    ]

    # If a specific ward is required,
    # only consider beds from that ward.
    if required_ward:
        candidate_beds = [
            bed
            for bed in candidate_beds
            if bed.ward.lower() == required_ward.lower()
        ]

    if not candidate_beds:
        return None

    # Critical/high priority patients prefer ICU.
    if level in {"critical", "high"}:

        icu_beds = [
            bed
            for bed in candidate_beds
            if bed.ward.lower() == "icu"
        ]

        if icu_beds:
            return sorted(
                icu_beds,
                key=lambda bed: bed.bed_id
            )[0]

    return sorted(
        candidate_beds,
        key=lambda bed: bed.bed_id
    )[0]


def find_future_bed(
    beds,
    emergency_level: str,
    required_ward: str | None
):
    """
    Find an occupied bed that is expected
    to become available in the future.
    """

    now = datetime.now()

    candidate_beds = [
        bed
        for bed in beds
        if bed.status == "occupied"
        and bed.expected_release_at is not None
        and bed.expected_release_at > now
    ]

    if required_ward:
        candidate_beds = [
            bed
            for bed in candidate_beds
            if bed.ward.lower() == required_ward.lower()
        ]

    if not candidate_beds:
        return None

    level = emergency_level.lower()

    # Critical/high patients prefer future ICU beds.
    if level in {"critical", "high"}:

        icu_beds = [
            bed
            for bed in candidate_beds
            if bed.ward.lower() == "icu"
        ]

        if icu_beds:
            return sorted(
                icu_beds,
                key=lambda bed: bed.expected_release_at
            )[0]

    return sorted(
        candidate_beds,
        key=lambda bed: bed.expected_release_at
    )[0]


# =========================================================
# REALLOCATION HELPERS
# =========================================================

def find_reallocation_candidate(
    db: Session,
    beds,
    target_patient_id: str,
    required_ward: str
):
    """
    Find an occupied bed in the required ward whose
    current patient can potentially be reallocated.

    The target patient itself is excluded.
    """

    candidate_beds = [
        bed
        for bed in beds
        if bed.status == "occupied"
        and bed.patient_id
        and bed.patient_id != target_patient_id
        and bed.ward.lower() == required_ward.lower()
    ]

    for bed in sorted(
        candidate_beds,
        key=lambda bed: bed.bed_id
    ):

        allowed, reason = can_reallocate_patient(
            db,
            bed.patient_id
        )

        if allowed:
            return {
                "bed": bed,
                "current_patient_id": bed.patient_id,
                "reason": reason
            }

    return None


def find_replacement_bed(
    beds,
    current_ward: str,
    reserved_bed_ids: set
):
    """
    Find an available bed outside the current ward.

    reserved_bed_ids represents beds already reserved
    inside the current simulation.
    """

    candidate_beds = [
        bed
        for bed in beds
        if bed.status == "available"
        and bed.bed_id not in reserved_bed_ids
        and bed.ward.lower() != current_ward.lower()
    ]

    if not candidate_beds:
        return None

    return sorted(
        candidate_beds,
        key=lambda bed: bed.bed_id
    )[0]


# =========================================================
# STAFF HELPERS
# =========================================================

def find_staff_for_patient(
    staff,
    ward: str,
    reserved_staff_ids: set
):
    """
    Find available staff suitable for the ward.

    Simulation only.
    No database state is modified.
    """

    available_staff = [
        member
        for member in staff
        if member.status == "available"
        and member.staff_id not in reserved_staff_ids
        and member.department
        and member.department.lower() == ward.lower()
    ]

    if not available_staff:
        return None

    return sorted(
        available_staff,
        key=lambda member: member.staff_id
    )[0]


# =========================================================
# EQUIPMENT HELPERS
# =========================================================

def find_equipment_for_patient(
    equipment,
    ward: str,
    reserved_equipment_ids: set
):
    """
    Find available equipment located in the required ward.

    Simulation only.
    """

    available_equipment = [
        item
        for item in equipment
        if item.status == "available"
        and item.equipment_id not in reserved_equipment_ids
        and item.location
        and item.location.lower() == ward.lower()
    ]

    if not available_equipment:
        return None

    return sorted(
        available_equipment,
        key=lambda item: item.equipment_id
    )[0]


# =========================================================
# SCORING
# =========================================================

def calculate_action_score(
    emergency_level: str,
    action_type: str,
    has_staff: bool,
    has_equipment: bool,
    constraints: list[str]
):
    """
    Deterministic score for a simulated action.

    This is NOT ML.
    This is NOT OR-Tools optimization.

    It is simply a transparent ranking mechanism.
    """

    score = 0

    level = emergency_level.lower()

    # -----------------------------------------------------
    # Patient priority
    # -----------------------------------------------------

    if level == "critical":
        score += 40

    elif level == "high":
        score += 30

    elif level == "medium":
        score += 20

    else:
        score += 10

    # -----------------------------------------------------
    # Action priority
    # -----------------------------------------------------

    if action_type == "immediate_allocation":
        score += 30

    elif action_type == "future_allocation":
        score += 15

    elif action_type == "reallocation":
        score += 10

    # -----------------------------------------------------
    # Resource completeness
    # -----------------------------------------------------

    if has_staff:
        score += 15

    if has_equipment:
        score += 15

    # -----------------------------------------------------
    # Constraint penalty
    # -----------------------------------------------------

    score -= len(constraints) * 5

    return score


# =========================================================
# CANDIDATE GENERATION
# =========================================================

def generate_candidates(
    db: Session,
    patient_id: str,
    emergency_level: str,
    required_ward: str | None,
    simulation_state: dict,
    reserved_beds: set[str],
    reserved_staff: set[str],
    reserved_equipment: set[str]
):
    """
    Generate ALL feasible candidate actions
    for one simulated patient.

    The database is never modified.

    Candidates are later ranked by score.
    """

    candidates = []

    beds = simulation_state["beds"]
    staff = simulation_state["staff"]
    equipment = simulation_state["equipment"]

    # =====================================================
    # 1. IMMEDIATE ALLOCATION CANDIDATES
    # =====================================================

    available_beds = [
        bed
        for bed in beds
        if bed.status == "available"
        and bed.bed_id not in reserved_beds
    ]

    if required_ward:
        available_beds = [
            bed
            for bed in available_beds
            if bed.ward.lower() == required_ward.lower()
        ]

    for bed in sorted(
        available_beds,
        key=lambda item: item.bed_id
    ):

        staff_member = find_staff_for_patient(
            staff,
            bed.ward,
            reserved_staff
        )

        equipment_item = find_equipment_for_patient(
            equipment,
            bed.ward,
            reserved_equipment
        )

        constraints = []

        if required_ward:
            constraints.append(
                f"{required_ward} bed required"
            )

        if not staff_member:
            constraints.append(
                f"No available staff found for {bed.ward}"
            )

        if not equipment_item:
            constraints.append(
                f"No available equipment found in {bed.ward}"
            )

        score = calculate_action_score(
            emergency_level=emergency_level,
            action_type="immediate_allocation",
            has_staff=staff_member is not None,
            has_equipment=equipment_item is not None,
            constraints=constraints
        )

        candidate = RecommendationCandidate(
            action_type="immediate_allocation",

            patient_id=patient_id,

            recommended_bed_id=bed.bed_id,

            recommended_staff_id=(
                staff_member.staff_id
                if staff_member
                else None
            ),

            recommended_equipment_id=(
                equipment_item.equipment_id
                if equipment_item
                else None
            ),

            # New simulated patient has no current assignment.
            current_bed_id=None,
            current_staff_id=None,
            current_equipment_id=None,

            constraints=constraints,

            score=score,

            reason=(
                f"Bed {bed.bed_id} is available "
                f"in {bed.ward}."
            ),

            expected_impact=(
                f"{patient_id} can be allocated "
                f"to {bed.bed_id} immediately."
            ),

            feasible=True
        )

        candidates.append(candidate)

    # =====================================================
    # 2. FUTURE RELEASE CANDIDATES
    # =====================================================

    now = datetime.now()

    future_beds = [
        bed
        for bed in beds
        if bed.status == "occupied"
        and bed.bed_id not in reserved_beds
        and bed.expected_release_at is not None
        and bed.expected_release_at > now
    ]

    if required_ward:
        future_beds = [
            bed
            for bed in future_beds
            if bed.ward.lower() == required_ward.lower()
        ]

    for bed in sorted(
        future_beds,
        key=lambda item: item.expected_release_at
    ):

        constraints = [
            "Bed is currently occupied",
            "Bed must be released before allocation"
        ]

        if required_ward:
            constraints.append(
                f"{required_ward} bed required"
            )

        score = calculate_action_score(
            emergency_level=emergency_level,
            action_type="future_allocation",
            has_staff=False,
            has_equipment=False,
            constraints=constraints
        )

        candidate = RecommendationCandidate(
            action_type="future_allocation",

            patient_id=patient_id,

            recommended_bed_id=bed.bed_id,

            recommended_staff_id=None,
            recommended_equipment_id=None,

            current_bed_id=None,
            current_staff_id=None,
            current_equipment_id=None,

            constraints=constraints,

            score=score,

            reason=(
                f"Bed {bed.bed_id} is currently occupied "
                f"but is expected to be released at "
                f"{bed.expected_release_at}."
            ),

            expected_impact=(
                f"{patient_id} can be considered for "
                f"{bed.bed_id} after its release."
            ),

            feasible=True
        )

        candidates.append(candidate)

    # =====================================================
    # 3. REALLOCATION CANDIDATES
    # =====================================================

    if required_ward:

        occupied_candidates = [
            bed
            for bed in beds
            if bed.status == "occupied"
            and bed.bed_id not in reserved_beds
            and bed.patient_id
            and bed.ward.lower() == required_ward.lower()
            and bed.patient_id != patient_id
        ]

        for occupied_bed in sorted(
            occupied_candidates,
            key=lambda item: item.bed_id
        ):

            reallocation = find_reallocation_candidate(
                db,
                [occupied_bed],
                patient_id,
                required_ward
            )

            if not reallocation:
                continue

            replacement_bed = find_replacement_bed(
                beds,
                occupied_bed.ward,
                reserved_beds
            )

            if not replacement_bed:
                continue

            affected_patient_id = (
                reallocation["current_patient_id"]
            )

            current_staff = find_staff_for_patient(
                staff,
                occupied_bed.ward,
                reserved_staff
            )

            current_equipment = find_equipment_for_patient(
                equipment,
                occupied_bed.ward,
                reserved_equipment
            )

            constraints = [
                f"{required_ward} bed required",

                (
                    f"Patient {affected_patient_id} "
                    "can be considered for reallocation"
                ),

                (
                    f"Replacement bed "
                    f"{replacement_bed.bed_id} available"
                )
            ]

            score = calculate_action_score(
                emergency_level=emergency_level,
                action_type="reallocation",
                has_staff=current_staff is not None,
                has_equipment=current_equipment is not None,
                constraints=constraints
            )

            candidate = RecommendationCandidate(
                action_type="reallocation",

                patient_id=patient_id,

                # New patient will receive the occupied ICU bed
                # after the current patient is moved.
                recommended_bed_id=occupied_bed.bed_id,

                recommended_staff_id=None,
                recommended_equipment_id=None,

                # IMPORTANT FIX:
                # Target simulated patient is currently unassigned.
                current_bed_id=None,
                current_staff_id=None,
                current_equipment_id=None,

                constraints=constraints,

                score=score,

                reason=(
                    f"No {required_ward} bed is currently "
                    f"available. Patient "
                    f"{affected_patient_id} can potentially "
                    f"be moved from "
                    f"{occupied_bed.bed_id} to "
                    f"{replacement_bed.bed_id}."
                ),

                expected_impact=(
                    f"Free {occupied_bed.bed_id} for "
                    f"{patient_id} while reallocating "
                    f"{affected_patient_id}."
                ),

                feasible=True
            )

            candidates.append(candidate)

    # =====================================================
    # SORT CANDIDATES
    # =====================================================

    candidates.sort(
        key=lambda candidate: (
            -candidate.score,
            candidate.recommended_bed_id or ""
        )
    )

    return candidates


# =========================================================
# MAIN WHAT-IF SIMULATION
# =========================================================

def simulate_scenario(
    db: Session,
    patients: list
):
    """
    Run the complete what-if simulation.

    IMPORTANT:
    The real database is NEVER modified.

    All hypothetical resource reservations exist
    only inside this function.
    """

    state = get_simulation_state(db)

    beds = state["beds"]
    staff = state["staff"]
    equipment = state["equipment"]

    # =====================================================
    # HYPOTHETICAL SIMULATION STATE
    # =====================================================

    simulated_bed_ids = set()
    simulated_staff_ids = set()
    simulated_equipment_ids = set()

    recommendations = []

    # =====================================================
    # PROCESS EACH SIMULATED PATIENT
    # =====================================================

    for patient in patients:

        candidates = generate_candidates(
            db=db,

            patient_id=patient.patient_id,

            emergency_level=patient.emergency_level,

            required_ward=patient.required_ward,

            simulation_state=state,

            reserved_beds=simulated_bed_ids,

            reserved_staff=simulated_staff_ids,

            reserved_equipment=simulated_equipment_ids
        )

        # =================================================
        # NO FEASIBLE CANDIDATE
        # =================================================

        if not candidates:

            recommendations.append({
                "patient_id": patient.patient_id,

                "emergency_level": (
                    patient.emergency_level
                ),

                "status": "no_feasible_action",

                "recommendation_type": None,

                "recommended_action": None,

                "alternatives": [],

                "reason": (
                    "No suitable immediate bed, "
                    "future-release bed, or safe "
                    "reallocation option was found."
                ),

                "constraints": [
                    (
                        "All suitable resources are either "
                        "occupied, unavailable, or reserved "
                        "in the simulation."
                    )
                ],

                "expected_impact": (
                    "Patient remains without a simulated "
                    "resource allocation."
                ),

                "human_decision_required": True,

                "candidate_count": 0
            })

            continue

        # =================================================
        # TOP RECOMMENDATION
        # =================================================

        top_candidate = candidates[0]

        # =================================================
        # ALTERNATIVES
        # =================================================

        alternatives = []

        for candidate in candidates[1:]:

            alternative = {
                "action_type": candidate.action_type,

                "bed_id": (
                    candidate.recommended_bed_id
                ),

                "staff_id": (
                    candidate.recommended_staff_id
                ),

                "equipment_id": (
                    candidate.recommended_equipment_id
                ),

                "score": candidate.score,

                "reason": candidate.reason
            }

            # Add complete affected entity details
            # for reallocation alternatives.
            if candidate.action_type == "reallocation":

                selected_bed = next(
                    (
                        bed
                        for bed in beds
                        if bed.bed_id ==
                        candidate.recommended_bed_id
                    ),
                    None
                )

                if selected_bed and selected_bed.patient_id:

                    replacement_bed = find_replacement_bed(
                        beds,
                        selected_bed.ward,
                        simulated_bed_ids
                    )

                    alternative["affected_entities"] = [
                        {
                            "entity_type": "patient",
                            "entity_id": selected_bed.patient_id,

                            "current_assignment": {
                                "bed_id": selected_bed.bed_id,
                                "staff_id": None,
                                "equipment_id": None
                            },

                            "proposed_assignment": {
                                "bed_id": (
                                    replacement_bed.bed_id
                                    if replacement_bed
                                    else None
                                ),
                                "staff_id": None,
                                "equipment_id": None
                            },

                            "reason": (
                                f"Reallocation of "
                                f"{selected_bed.patient_id} "
                                f"can free "
                                f"{selected_bed.bed_id} "
                                f"for {patient.patient_id}."
                            )
                        }
                    ]

            alternatives.append(alternative)

        # =================================================
        # BUILD FINAL PERSONALIZED RECOMMENDATION
        # =================================================

        recommendation = {

            "patient_id": patient.patient_id,

            "emergency_level": patient.emergency_level,

            "status": "feasible",

            "recommendation_type": (
                top_candidate.action_type
            ),

            "score": top_candidate.score,

            "recommended_action": {

                "patient_id": patient.patient_id,

                "current_assignment": {

                    "bed_id": (
                        top_candidate.current_bed_id
                    ),

                    "staff_id": (
                        top_candidate.current_staff_id
                    ),

                    "equipment_id": (
                        top_candidate.current_equipment_id
                    )
                },

                "proposed_assignment": {

                    "bed_id": (
                        top_candidate.recommended_bed_id
                    ),

                    "staff_id": (
                        top_candidate.recommended_staff_id
                    ),

                    "equipment_id": (
                        top_candidate.recommended_equipment_id
                    )
                }
            },

            "reason": top_candidate.reason,

            "constraints": top_candidate.constraints,

            "expected_impact": (
                top_candidate.expected_impact
            ),

            "alternatives": alternatives,

            "candidate_count": len(candidates),

            "human_decision_required": True
        }

        # =================================================
        # REALLOCATION DETAILS
        # =================================================

        if top_candidate.action_type == "reallocation":

            affected_patient_id = None

            # Find affected patient using the selected bed.
            selected_bed = next(
                (
                    bed
                    for bed in beds
                    if bed.bed_id ==
                    top_candidate.recommended_bed_id
                ),
                None
            )

            if selected_bed:
                affected_patient_id = (
                    selected_bed.patient_id
                )

            replacement_bed = find_replacement_bed(
                beds,
                selected_bed.ward
                if selected_bed
                else patient.required_ward,
                simulated_bed_ids
            )

            recommendation["affected_entities"] = []

            if affected_patient_id:

                affected_entity = {

                    "entity_type": "patient",

                    "entity_id": affected_patient_id,

                    "current_assignment": {

                        "bed_id": (
                            top_candidate.recommended_bed_id
                        ),

                        "staff_id": None,

                        "equipment_id": None
                    },

                    "proposed_assignment": {

                        "bed_id": (
                            replacement_bed.bed_id
                            if replacement_bed
                            else None
                        ),

                        "staff_id": None,

                        "equipment_id": None
                    },

                    "reason": (
                        f"Reallocation of "
                        f"{affected_patient_id} can free "
                        f"{top_candidate.recommended_bed_id} "
                        f"for {patient.patient_id}."
                    )
                }

                recommendation[
                    "affected_entities"
                ].append(affected_entity)

        else:

            recommendation["affected_entities"] = []

        recommendations.append(
            recommendation
        )

        # =================================================
        # RESERVE HYPOTHETICAL RESOURCES
        # =================================================

        if top_candidate.recommended_bed_id:

            simulated_bed_ids.add(
                top_candidate.recommended_bed_id
            )

        if top_candidate.recommended_staff_id:

            simulated_staff_ids.add(
                top_candidate.recommended_staff_id
            )

        if top_candidate.recommended_equipment_id:

            simulated_equipment_ids.add(
                top_candidate.recommended_equipment_id
            )

        # For reallocation, reserve the replacement bed too.
        if top_candidate.action_type == "reallocation":

            selected_bed = next(
                (
                    bed
                    for bed in beds
                    if bed.bed_id ==
                    top_candidate.recommended_bed_id
                ),
                None
            )

            if selected_bed:

                replacement_bed = find_replacement_bed(
                    beds,
                    selected_bed.ward,
                    simulated_bed_ids
                )

                if replacement_bed:

                    simulated_bed_ids.add(
                        replacement_bed.bed_id
                    )

    # =====================================================
    # FINAL RESULT
    # =====================================================

    return {

        "simulation": True,

        "database_modified": False,

        "patients_simulated": len(patients),

        "resources_reserved_in_simulation": {

            "beds": sorted(
                simulated_bed_ids
            ),

            "staff": sorted(
                simulated_staff_ids
            ),

            "equipment": sorted(
                simulated_equipment_ids
            )
        },

        "recommendations": recommendations
    }
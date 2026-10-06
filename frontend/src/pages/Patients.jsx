import { useEffect, useMemo, useState } from "react";

import {
  Users,
  Clock3,
  CircleCheck,
  TriangleAlert,
  Search,
  RefreshCw,
  BedDouble,
  UserRound,
  MonitorCog,
  Plus,
  X,
  Siren,
} from "lucide-react";

import api from "../services/api";
import "./Patients.css";

function Patients() {
  const [patients, setPatients] = useState([]);
  const [assignments, setAssignments] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("all");
  const [status, setStatus] = useState("all");

  const [dischargingPatientId, setDischargingPatientId] = useState("");
  const [dischargeError, setDischargeError] = useState("");

  /* =========================================================
     PATIENT ARRIVAL
  ========================================================= */

  const [showArrivalForm, setShowArrivalForm] = useState(false);
  const [arrivalSubmitting, setArrivalSubmitting] = useState(false);
  const [arrivalError, setArrivalError] = useState("");
  const [arrivalResult, setArrivalResult] = useState(null);

  const [arrivalForm, setArrivalForm] = useState({
    patient_id: "",
    name: "",
    age: "",
    emergency_level: "high",
    status: "waiting",
  });

  /* =========================================================
     FETCH PATIENTS
  ========================================================= */

  const fetchPatients = async (showRefresh = false) => {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const [patientsResponse, assignmentsResponse] =
        await Promise.all([
          api.get("/patients"),
          api.get("/assignments/current"),
        ]);

      setPatients(
        Array.isArray(patientsResponse.data)
          ? patientsResponse.data
          : []
      );

      setAssignments(
        Array.isArray(assignmentsResponse.data)
          ? assignmentsResponse.data
          : []
      );
    } catch (err) {
      console.error("Failed to fetch patient data:", err);

      setError(
        err?.response?.data?.detail ||
          "Unable to load patient data."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /* =========================================================
     DISCHARGE
  ========================================================= */

  const handleDischarge = async (patient) => {
    const confirmed = window.confirm(
      `Discharge ${patient.name} (${patient.patient_id})?\n\n` +
        "This will mark the patient as discharged and place the occupied bed into turnover-required status."
    );

    if (!confirmed) {
      return;
    }

    try {
      setDischargeError("");
      setDischargingPatientId(patient.patient_id);

      await api.post(
        `/patients/${patient.patient_id}/discharge`
      );

      await fetchPatients(true);
    } catch (err) {
      console.error("Patient discharge failed:", err);

      setDischargeError(
        err?.response?.data?.detail ||
          `Unable to discharge ${patient.patient_id}.`
      );
    } finally {
      setDischargingPatientId("");
    }
  };

  /* =========================================================
     PATIENT ARRIVAL FORM
  ========================================================= */

  const handleArrivalInputChange = (event) => {
    const { name, value } = event.target;

    setArrivalForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const openArrivalForm = () => {
    setArrivalError("");
    setArrivalResult(null);

    setArrivalForm({
      patient_id: "",
      name: "",
      age: "",
      emergency_level: "high",
      status: "waiting",
    });

    setShowArrivalForm(true);
  };

  const closeArrivalForm = () => {
    if (arrivalSubmitting) {
      return;
    }

    setShowArrivalForm(false);
    setArrivalError("");
  };

  const handlePatientArrival = async (event) => {
    event.preventDefault();

    setArrivalError("");
    setArrivalResult(null);

    const patientId = arrivalForm.patient_id.trim();
    const patientName = arrivalForm.name.trim();
    const age = Number(arrivalForm.age);

    if (!patientId) {
      setArrivalError("Patient ID is required.");
      return;
    }

    if (!patientName) {
      setArrivalError("Patient name is required.");
      return;
    }

    if (!arrivalForm.age || !Number.isInteger(age) || age <= 0) {
      setArrivalError("Please enter a valid age.");
      return;
    }

    try {
      setArrivalSubmitting(true);

      const response = await api.post("/events", {
        event_type: "PATIENT_ARRIVAL",
        patient: {
          patient_id: patientId,
          name: patientName,
          age,
          emergency_level: arrivalForm.emergency_level,
          status: "waiting",
        },
      });

      const result = response.data;

      setArrivalResult(result);

      await fetchPatients(true);
    } catch (err) {
      console.error("Patient arrival failed:", err);

      setArrivalError(
        err?.response?.data?.detail ||
          "Unable to process patient arrival."
      );
    } finally {
      setArrivalSubmitting(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  /* =========================================================
     ASSIGNMENT MAP
  ========================================================= */

  const assignmentMap = useMemo(() => {
    const map = {};

    assignments.forEach((assignment) => {
      map[assignment.patient_id] = assignment;
    });

    return map;
  }, [assignments]);

  /* =========================================================
     FILTERED PATIENTS
  ========================================================= */

  const filteredPatients = useMemo(() => {
    const query = search.trim().toLowerCase();

    return patients.filter((patient) => {
      const matchesSearch =
        !query ||
        String(patient.patient_id || "")
          .toLowerCase()
          .includes(query) ||
        String(patient.name || "")
          .toLowerCase()
          .includes(query);

      const matchesPriority =
        priority === "all" ||
        String(patient.emergency_level || "").toLowerCase() ===
          priority;

      const matchesStatus =
        status === "all" ||
        String(patient.status || "").toLowerCase() ===
          status;

      return (
        matchesSearch &&
        matchesPriority &&
        matchesStatus
      );
    });
  }, [patients, search, priority, status]);

  /* =========================================================
     STATS
  ========================================================= */

  const totalPatients = patients.length;

  const waitingPatients = patients.filter(
    (patient) =>
      String(patient.status || "").toLowerCase() === "waiting"
  ).length;

  const admittedPatients = patients.filter(
    (patient) =>
      String(patient.status || "").toLowerCase() === "admitted"
  ).length;

  const criticalPatients = patients.filter(
    (patient) =>
      String(patient.emergency_level || "").toLowerCase() ===
      "critical"
  ).length;

  /* =========================================================
     HELPERS
  ========================================================= */

  const getPriorityClass = (level) => {
    const value = String(level || "").toLowerCase();

    if (value === "critical") return "critical";
    if (value === "high") return "high";
    if (value === "medium") return "medium";

    return "low";
  };

  const getStatusClass = (value) => {
    const statusValue = String(value || "").toLowerCase();

    if (statusValue === "admitted") return "admitted";
    if (statusValue === "waiting") return "waiting";

    return "other";
  };

  /* =========================================================
     OPERATIONAL STATE
  ========================================================= */

  const renderOperationalState = (patient) => {
    const patientStatus = String(
      patient.status || ""
    ).toLowerCase();

    if (patientStatus === "discharged") {
      return (
        <div className="operational-state discharged-state">
          <CircleCheck size={16} />
          <span>Discharged</span>
        </div>
      );
    }

    const assignment = assignmentMap[patient.patient_id];

    if (!assignment) {
      return (
        <div className="operational-state waiting-state">
          <Clock3 size={16} />
          <span>Waiting for allocation</span>
        </div>
      );
    }

    const resources = [];

    if (assignment.bed_id) {
      resources.push(
        <span key="bed" className="allocation-item">
          <BedDouble size={14} />
          {assignment.bed_id}
        </span>
      );
    }

    if (assignment.staff_id) {
      resources.push(
        <span key="staff" className="allocation-item">
          <UserRound size={14} />
          {assignment.staff_id}
        </span>
      );
    }

    if (assignment.equipment_id) {
      resources.push(
        <span key="equipment" className="allocation-item">
          <MonitorCog size={14} />
          {assignment.equipment_id}
        </span>
      );
    }

    return (
      <div className="operational-state allocated-state">
        <CircleCheck size={16} />

        <div className="allocation-details">
          <span className="allocation-label">
            Allocated
          </span>

          <div className="allocation-items">
            {resources.length > 0 ? (
              resources
            ) : (
              <span className="allocation-item">
                Assignment recorded
              </span>
            )}
          </div>
        </div>
      </div>
    );
  };

  /* =========================================================
     RENDER
  ========================================================= */

  return (
    <main className="patients-page">
      <div className="patients-content">

        {/* =====================================================
            HEADER
        ===================================================== */}

        <section className="patients-header">
          <div>
            <div className="patients-eyebrow">
              <Users size={15} />
              <span>PATIENT OPERATIONS</span>
            </div>

            <h1>Patients</h1>

            <p>
              Monitor patient status, emergency priority,
              and operational allocation state.
            </p>
          </div>

          <div className="patients-header-actions">
            <button
              type="button"
              className="patient-arrival-button"
              onClick={openArrivalForm}
            >
              <Plus size={17} />
              Patient Arrival
            </button>

            <button
              className="patients-refresh"
              onClick={() => fetchPatients(true)}
              disabled={refreshing}
            >
              <RefreshCw
                size={17}
                className={refreshing ? "spin" : ""}
              />

              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </section>

        {/* =====================================================
            PATIENT ARRIVAL FORM
        ===================================================== */}

        {showArrivalForm && (
          <section className="patient-arrival-card">
            <div className="patient-arrival-header">
              <div>
                <div className="patient-arrival-eyebrow">
                  <Siren size={15} />
                  <span>EMERGENCY INTAKE</span>
                </div>

                <h2>Patient Arrival</h2>

                <p>
                  Register a new arrival and generate an
                  AI-assisted resource recommendation.
                </p>
              </div>

              <button
                type="button"
                className="patient-arrival-close"
                onClick={closeArrivalForm}
                disabled={arrivalSubmitting}
                aria-label="Close patient arrival form"
              >
                <X size={18} />
              </button>
            </div>

            <form
              className="patient-arrival-form"
              onSubmit={handlePatientArrival}
            >
              <div className="patient-arrival-field">
                <label htmlFor="patient_id">
                  Patient ID
                </label>

                <input
                  id="patient_id"
                  name="patient_id"
                  type="text"
                  placeholder="e.g. EVT-003"
                  value={arrivalForm.patient_id}
                  onChange={handleArrivalInputChange}
                  disabled={arrivalSubmitting}
                />
              </div>

              <div className="patient-arrival-field">
                <label htmlFor="name">
                  Patient Name
                </label>

                <input
                  id="name"
                  name="name"
                  type="text"
                  placeholder="e.g. Raj Kumar"
                  value={arrivalForm.name}
                  onChange={handleArrivalInputChange}
                  disabled={arrivalSubmitting}
                />
              </div>

              <div className="patient-arrival-field">
                <label htmlFor="age">
                  Age
                </label>

                <input
                  id="age"
                  name="age"
                  type="number"
                  min="1"
                  placeholder="e.g. 65"
                  value={arrivalForm.age}
                  onChange={handleArrivalInputChange}
                  disabled={arrivalSubmitting}
                />
              </div>

              <div className="patient-arrival-field">
                <label htmlFor="emergency_level">
                  Emergency Level
                </label>

                <select
                  id="emergency_level"
                  name="emergency_level"
                  value={arrivalForm.emergency_level}
                  onChange={handleArrivalInputChange}
                  disabled={arrivalSubmitting}
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div className="patient-arrival-field">
                <label htmlFor="arrival_status">
                  Initial Status
                </label>

                <input
                  id="arrival_status"
                  type="text"
                  value="Waiting"
                  disabled
                />
              </div>

              <div className="patient-arrival-actions">
                <button
                  type="button"
                  className="patient-arrival-cancel"
                  onClick={closeArrivalForm}
                  disabled={arrivalSubmitting}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="patient-arrival-submit"
                  disabled={arrivalSubmitting}
                >
                  {arrivalSubmitting
                    ? "Processing Arrival..."
                    : "Process Arrival"}
                </button>
              </div>
            </form>

            {arrivalError && (
              <div className="patient-arrival-error">
                {arrivalError}
              </div>
            )}

            {arrivalResult && (
              <div className="patient-arrival-result">
                <div className="patient-arrival-result-title">
                  <CircleCheck size={18} />
                  <strong>Patient Arrival Processed</strong>
                </div>

                <div className="patient-arrival-result-grid">
                  <div>
                    <span>Patient</span>
                    <strong>
                      {arrivalResult.event?.name || "—"}
                    </strong>
                    <small>
                      {arrivalResult.event?.patient_id || "—"}
                    </small>
                  </div>

                  <div>
                    <span>Recommendation</span>
                    <strong>
                      #
                      {arrivalResult.resource_coordination
                        ?.recommendation_id || "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Recommended Bed</span>
                    <strong>
                      {arrivalResult.resource_coordination
                        ?.recommended_resources?.bed_id || "None"}
                    </strong>
                    <small>
                      {arrivalResult.resource_coordination
                        ?.recommended_resources?.ward || "—"}
                    </small>
                  </div>

                  <div>
                    <span>Staff</span>
                    <strong>
                      {arrivalResult.resource_coordination
                        ?.resource_status?.staff ===
                      "staff_required"
                        ? "Required"
                        : arrivalResult.resource_coordination
                              ?.resource_status?.staff ||
                          "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Equipment</span>
                    <strong>
                      {arrivalResult.resource_coordination
                        ?.resource_status?.equipment ||
                        "—"}
                    </strong>
                  </div>

                  <div>
                    <span>Human Decision</span>
                    <strong>
                      {arrivalResult.resource_coordination
                        ?.human_decision_required
                        ? "Required"
                        : "Not required"}
                    </strong>
                  </div>
                </div>

                <div className="patient-arrival-result-note">
                  Resources remain unchanged until the
                  recommendation is approved by an authorized
                  human decision-maker.
                </div>

                <button
                  type="button"
                  className="patient-arrival-done"
                  onClick={() => {
                    setShowArrivalForm(false);
                    setArrivalResult(null);
                  }}
                >
                  Done
                </button>
              </div>
            )}
          </section>
        )}

        {/* =====================================================
            STATS
        ===================================================== */}

        <section className="patients-stats">

          <div className="patient-stat-card">
            <div className="patient-stat-icon blue">
              <Users size={19} />
            </div>

            <div>
              <span>Total Patients</span>
              <strong>{totalPatients}</strong>
            </div>
          </div>

          <div className="patient-stat-card">
            <div className="patient-stat-icon amber">
              <Clock3 size={19} />
            </div>

            <div>
              <span>Waiting</span>
              <strong>{waitingPatients}</strong>
            </div>
          </div>

          <div className="patient-stat-card">
            <div className="patient-stat-icon green">
              <CircleCheck size={19} />
            </div>

            <div>
              <span>Admitted</span>
              <strong>{admittedPatients}</strong>
            </div>
          </div>

          <div className="patient-stat-card">
            <div className="patient-stat-icon red">
              <TriangleAlert size={19} />
            </div>

            <div>
              <span>Critical</span>
              <strong>{criticalPatients}</strong>
            </div>
          </div>

        </section>

        {/* =====================================================
            FILTERS
        ===================================================== */}

        <section className="patients-filter-bar">

          <div className="patient-search">
            <Search size={17} />

            <input
              type="text"
              placeholder="Search patient ID or name"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
            />
          </div>

          <select
            value={priority}
            onChange={(event) =>
              setPriority(event.target.value)
            }
          >
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={status}
            onChange={(event) =>
              setStatus(event.target.value)
            }
          >
            <option value="all">All Status</option>
            <option value="waiting">Waiting</option>
            <option value="admitted">Admitted</option>
          </select>

        </section>

        {/* =====================================================
            ERRORS
        ===================================================== */}

        {error && (
          <div className="patients-error">
            {error}
          </div>
        )}

        {dischargeError && (
          <div className="patients-error">
            {dischargeError}
          </div>
        )}

        {/* =====================================================
            PATIENT TABLE
        ===================================================== */}

        <section className="patients-table-card">

          <div className="patients-table-header">
            <div>
              <span>LIVE DATABASE</span>
              <h2>Patient records</h2>
            </div>

            <strong>
              {filteredPatients.length} records
            </strong>
          </div>

          {loading ? (
            <div className="patients-loading">
              Loading patient data...
            </div>
          ) : filteredPatients.length === 0 ? (
            <div className="patients-empty">
              <Users size={28} />

              <h3>No patients found</h3>

              <p>
                Try changing your search or filter criteria.
              </p>
            </div>
          ) : (
            <div className="patients-table-scroll">

              <table className="patients-table">

                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Age</th>
                    <th>Emergency Level</th>
                    <th>Status</th>
                    <th>Operational State</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>

                  {filteredPatients.map((patient) => (
                    <tr key={patient.patient_id}>

                      <td>
                        <div className="patient-identity">
                          <strong>
                            {patient.name}
                          </strong>

                          <span>
                            {patient.patient_id}
                          </span>
                        </div>
                      </td>

                      <td className="patient-age">
                        {patient.age}
                      </td>

                      <td>
                        <span
                          className={`priority-pill ${getPriorityClass(
                            patient.emergency_level
                          )}`}
                        >
                          {patient.emergency_level}
                        </span>
                      </td>

                      <td>
                        <span
                          className={`status-pill ${getStatusClass(
                            patient.status
                          )}`}
                        >
                          {patient.status}
                        </span>
                      </td>

                      <td>
                        {renderOperationalState(patient)}
                      </td>

                      <td>
                        {String(
                          patient.status || ""
                        ).toLowerCase() === "admitted" ? (
                          <button
                            type="button"
                            className="patient-discharge-button"
                            onClick={() =>
                              handleDischarge(patient)
                            }
                            disabled={
                              dischargingPatientId ===
                              patient.patient_id
                            }
                          >
                            {dischargingPatientId ===
                            patient.patient_id
                              ? "Discharging..."
                              : "Discharge"}
                          </button>
                        ) : (
                          <span className="patient-action-muted">
                            —
                          </span>
                        )}
                      </td>

                    </tr>
                  ))}

                </tbody>

              </table>

            </div>
          )}

        </section>

      </div>

    </main>
  );
}

export default Patients;
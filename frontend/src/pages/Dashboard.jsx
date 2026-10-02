import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bed,
  Brain,
  CheckCircle2,
  Clock3,
  Cpu,
  HeartPulse,
  Users,
  AlertTriangle,
  Siren,
  Stethoscope,
  Zap,
} from "lucide-react";

import api from "../services/api";

function Dashboard() {
  const [patients, setPatients] = useState([]);
  const [beds, setBeds] = useState([]);
  const [staff, setStaff] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState("Checking...");
  const [systemMessage, setSystemMessage] = useState("");

  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);

    try {
      const [
        helloResponse,
        patientsResponse,
        bedsResponse,
        staffResponse,
        equipmentResponse,
        recommendationsResponse,
      ] = await Promise.all([
        api.get("/hello"),
        api.get("/patients"),
        api.get("/beds"),
        api.get("/staff"),
        api.get("/equipment"),
        api.get("/recommendations/pending"),
      ]);

      setPatients(patientsResponse.data || []);
      setBeds(bedsResponse.data || []);
      setStaff(staffResponse.data || []);
      setEquipment(equipmentResponse.data || []);
      setRecommendations(recommendationsResponse.data || []);

      setSystemStatus("Online");
      setSystemMessage(
        helloResponse.data?.message ||
          "Hospital API is running."
      );
    } catch (error) {
      console.error(
        "Dashboard data loading failed:",
        error
      );

      setSystemStatus("Offline");

      setSystemMessage(
        error.response?.data?.detail ||
          "Unable to load hospital operational data."
      );
    } finally {
      setLoading(false);
    }
  };

  /* =========================================================
     DERIVED RESOURCE DATA
  ========================================================= */

  const bedStats = useMemo(() => {
    const total = beds.length;

    const occupied = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "occupied"
    ).length;

    const available = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "available"
    ).length;

    const maintenance = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "maintenance"
    ).length;

    return {
      total,
      occupied,
      available,
      maintenance,
      occupancy:
        total > 0
          ? Math.round((occupied / total) * 100)
          : 0,
    };
  }, [beds]);

  const staffStats = useMemo(() => {
    const total = staff.length;

    const available = staff.filter(
      (member) =>
        String(member.status).toLowerCase() ===
        "available"
    ).length;

    const busy = staff.filter(
      (member) =>
        String(member.status).toLowerCase() ===
        "busy"
    ).length;

    return {
      total,
      available,
      busy,
    };
  }, [staff]);

  const equipmentStats = useMemo(() => {
    const total = equipment.length;

    const available = equipment.filter(
      (item) =>
        String(item.status).toLowerCase() ===
        "available"
    ).length;

    const occupied = equipment.filter(
      (item) =>
        String(item.status).toLowerCase() ===
        "occupied"
    ).length;

    return {
      total,
      available,
      occupied,
    };
  }, [equipment]);

  const wardStats = useMemo(() => {
    const getWardStats = (wardName) => {
      const wardBeds = beds.filter(
        (bed) =>
          String(bed.ward).toLowerCase() ===
          wardName.toLowerCase()
      );

      const total = wardBeds.length;

      const occupied = wardBeds.filter(
        (bed) =>
          String(bed.status).toLowerCase() ===
          "occupied"
      ).length;

      return {
        total,
        occupied,
        percentage:
          total > 0
            ? Math.round((occupied / total) * 100)
            : 0,
      };
    };

    return {
      icu: getWardStats("ICU"),
      general: getWardStats("General"),
      emergency: getWardStats("Emergency"),
    };
  }, [beds]);

  /* =========================================================
     CURRENT AI RECOMMENDATION
  ========================================================= */

  const currentRecommendation =
    recommendations.length > 0
      ? recommendations[0]
      : null;

  const recommendationPatient = currentRecommendation
    ? patients.find(
        (patient) =>
          patient.patient_id ===
          currentRecommendation.patient_id
      )
    : null;

  const patientCount = patients.length;

  const waitingPatients = patients.filter(
    (patient) =>
      String(patient.status).toLowerCase() ===
      "waiting"
  ).length;

  /* =========================================================
     RESOURCE CARDS
  ========================================================= */

  const resourceStats = [
    {
      label: "Patients",
      value: loading ? "—" : patientCount,
      detail: loading
        ? "Loading records..."
        : `${waitingPatients} waiting`,
      icon: Users,
      type: "blue",
    },
    {
      label: "Beds",
      value: loading
        ? "—"
        : `${bedStats.occupied} / ${bedStats.total}`,
      detail: loading
        ? "Loading resources..."
        : `${bedStats.occupancy}% occupied`,
      icon: Bed,
      type: "green",
    },
    {
      label: "Staff",
      value: loading ? "—" : staffStats.total,
      detail: loading
        ? "Loading staff..."
        : `${staffStats.available} available`,
      icon: Stethoscope,
      type: "purple",
    },
    {
      label: "Equipment",
      value: loading
        ? "—"
        : equipmentStats.total,
      detail: loading
        ? "Loading equipment..."
        : `${equipmentStats.occupied} active`,
      icon: Cpu,
      type: "orange",
    },
  ];

  /* =========================================================
     BOTTLENECKS
  ========================================================= */

  const bottlenecks = [
    {
      title: "ICU Capacity",
      detail:
        wardStats.icu.total > 0
          ? `${wardStats.icu.occupied} of ${wardStats.icu.total} ICU beds occupied`
          : "No ICU bed data available",
      value:
        wardStats.icu.total > 0
          ? `${wardStats.icu.percentage}%`
          : "—",
      status:
        wardStats.icu.percentage >= 90
          ? "critical"
          : wardStats.icu.percentage >= 75
            ? "warning"
            : "stable",
      icon: HeartPulse,
    },
    {
      title: "Waiting Patients",
      detail:
        waitingPatients > 0
          ? `${waitingPatients} patient(s) waiting for allocation`
          : "No waiting patients",
      value:
        waitingPatients > 0
          ? `${waitingPatients} waiting`
          : "Clear",
      status:
        waitingPatients >= 3
          ? "critical"
          : waitingPatients > 0
            ? "warning"
            : "stable",
      icon: Siren,
    },
    {
      title: "Staff Availability",
      detail:
        staffStats.total > 0
          ? `${staffStats.available} operational staff available`
          : "No staff data available",
      value:
        staffStats.total > 0
          ? `${staffStats.available} available`
          : "—",
      status:
        staffStats.total > 0 &&
        staffStats.available === 0
          ? "critical"
          : staffStats.available <= 2
            ? "warning"
            : "stable",
      icon: Users,
    },
  ];

  /* =========================================================
     ACTIVITY
  ========================================================= */

  const events = [
    {
      time: "LIVE",
      title: "Hospital state synchronized",
      detail: `${patientCount} patients · ${bedStats.total} beds`,
      icon: Activity,
      type: "info",
    },
    {
      time: "LIVE",
      title: "Resource availability updated",
      detail: `${bedStats.available} beds currently available`,
      icon: Bed,
      type: "success",
    },
    {
      time: "LIVE",
      title: "Staff state monitored",
      detail: `${staffStats.available} staff available`,
      icon: Users,
      type: "ai",
    },
    {
      time: "LIVE",
      title: "AI recommendations monitored",
      detail: `${recommendations.length} pending recommendation(s)`,
      icon: Brain,
      type: "warning",
    },
  ];

  /* =========================================================
     RENDER
  ========================================================= */

  return (
    <main className="dashboard-page">
      <div className="dashboard-container">

        {/* =====================================================
            HEADER
        ===================================================== */}

        <section className="command-header">
          <div>
            <div className="command-eyebrow">
              <span className="pulse-dot"></span>
              HOSPITAL OPERATIONS
            </div>

            <h1>
              Good evening,{" "}
              <span>
                {user?.name || "Hospital Admin"}
              </span>
            </h1>

            <p>
              Monitor hospital capacity, identify
              operational bottlenecks, and review
              AI-assisted resource actions.
            </p>
          </div>

          <div className="command-status">
            <div
              className={`status-indicator ${
                systemStatus === "Online"
                  ? "online"
                  : systemStatus === "Offline"
                    ? "offline"
                    : "checking"
              }`}
            ></div>

            <div>
              <strong>
                System {systemStatus}
              </strong>

              <span>
                {systemMessage ||
                  "Connecting to hospital API"}
              </span>
            </div>
          </div>
        </section>

        {/* =====================================================
            RESOURCE SNAPSHOT
        ===================================================== */}

        <section className="resource-snapshot">
          <div className="section-heading">
            <div>
              <span>RESOURCE SNAPSHOT</span>
              <h2>Hospital at a glance</h2>
            </div>

            <div className="live-badge">
              <Activity size={14} />
              Live monitoring
            </div>
          </div>

          <div className="resource-grid">
            {resourceStats.map((item) => {
              const Icon = item.icon;

              return (
                <div
                  className="resource-card"
                  key={item.label}
                >
                  <div className="resource-card-top">
                    <div
                      className={`resource-icon ${item.type}`}
                    >
                      <Icon size={20} />
                    </div>

                    <ArrowRight size={17} />
                  </div>

                  <div className="resource-value">
                    {item.value}
                  </div>

                  <div className="resource-label">
                    {item.label}
                  </div>

                  <div className="resource-detail">
                    {item.detail}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* =====================================================
            AI ACTION + CAPACITY
        ===================================================== */}

        <section className="main-command-grid">

          {/* AI RECOMMENDATION */}

          <div className="ai-action-card">
            <div className="ai-card-header">
              <div>
                <div className="section-label ai-label">
                  <Brain size={14} />
                  AI ACTION CENTER
                </div>

                <h2>
                  {currentRecommendation
                    ? "Pending operational recommendation"
                    : "No pending AI recommendation"}
                </h2>
              </div>

              {currentRecommendation && (
                <div className="priority-badge">
                  <span></span>
                  HUMAN REVIEW REQUIRED
                </div>
              )}
            </div>

            {currentRecommendation ? (
              <>
                <div className="recommendation-patient">
                  <div className="patient-avatar">
                    {String(
                      currentRecommendation.patient_id
                    ).charAt(0)}
                  </div>

                  <div>
                    <strong>
                      {currentRecommendation.patient_id}
                      {recommendationPatient
                        ? ` · ${recommendationPatient.name}`
                        : ""}
                    </strong>

                    <span>
                      {recommendationPatient?.emergency_level
                        ? `${recommendationPatient.emergency_level} priority`
                        : "Patient awaiting operational allocation"}
                    </span>
                  </div>
                </div>

                <div className="action-route">
                  <div className="route-block">
                    <span>CURRENT STATE</span>

                    <strong>
                      {recommendationPatient?.status ||
                        "Waiting"}
                    </strong>

                    <small>
                      Operational allocation pending
                    </small>
                  </div>

                  <ArrowRight
                    className="route-arrow"
                    size={22}
                  />

                  <div className="route-block recommended">
                    <span>RECOMMENDED BED</span>

                    <strong>
                      {currentRecommendation.recommended_bed_id ||
                        "Not specified"}
                    </strong>

                    <small>
                      {currentRecommendation.recommended_staff_id
                        ? `Staff: ${currentRecommendation.recommended_staff_id}`
                        : "Resource recommendation"}
                    </small>
                  </div>
                </div>

                <div className="recommendation-reason">
                  <div className="reason-icon">
                    <Zap size={16} />
                  </div>

                  <div>
                    <strong>
                      Why this action?
                    </strong>

                    <p>
                      {currentRecommendation.reason ||
                        "AI recommendation generated from current hospital state and allocation constraints."}
                    </p>
                  </div>
                </div>

                <div className="action-footer">
                  <div className="impact">
                    <span>DATABASE STATUS</span>

                    <strong>
                      {currentRecommendation.status ||
                        "pending"}
                    </strong>
                  </div>

                  <button className="review-button">
                    Review recommendation
                    <ArrowRight size={15} />
                  </button>
                </div>
              </>
            ) : (
              <div className="recommendation-empty">
                <CheckCircle2 size={30} />

                <strong>
                  Hospital operations currently have
                  no pending recommendation.
                </strong>

                <span>
                  New recommendations will appear here
                  when the recommendation engine generates
                  an actionable resource plan.
                </span>
              </div>
            )}
          </div>

          {/* CAPACITY */}

          <div className="capacity-card">
            <div className="card-title-row">
              <div>
                <span className="section-label">
                  CAPACITY
                </span>

                <h2>
                  Resource utilization
                </h2>
              </div>

              <Activity size={20} />
            </div>

            <div className="capacity-list">

              <div className="capacity-item">
                <div className="capacity-item-header">
                  <span>ICU</span>

                  <strong>
                    {wardStats.icu.total > 0
                      ? `${wardStats.icu.percentage}%`
                      : "—"}
                  </strong>
                </div>

                <div className="capacity-track">
                  <div
                    className="capacity-fill critical"
                    style={{
                      width: `${wardStats.icu.percentage}%`,
                    }}
                  ></div>
                </div>

                <small>
                  {wardStats.icu.total > 0
                    ? `${wardStats.icu.occupied} / ${wardStats.icu.total} occupied`
                    : "No ICU data"}
                </small>
              </div>

              <div className="capacity-item">
                <div className="capacity-item-header">
                  <span>General Ward</span>

                  <strong>
                    {wardStats.general.total > 0
                      ? `${wardStats.general.percentage}%`
                      : "—"}
                  </strong>
                </div>

                <div className="capacity-track">
                  <div
                    className="capacity-fill normal"
                    style={{
                      width: `${wardStats.general.percentage}%`,
                    }}
                  ></div>
                </div>

                <small>
                  {wardStats.general.total > 0
                    ? `${wardStats.general.occupied} / ${wardStats.general.total} occupied`
                    : "No General Ward data"}
                </small>
              </div>

              <div className="capacity-item">
                <div className="capacity-item-header">
                  <span>Emergency</span>

                  <strong>
                    {wardStats.emergency.total > 0
                      ? `${wardStats.emergency.percentage}%`
                      : "—"}
                  </strong>
                </div>

                <div className="capacity-track">
                  <div
                    className="capacity-fill warning"
                    style={{
                      width: `${wardStats.emergency.percentage}%`,
                    }}
                  ></div>
                </div>

                <small>
                  {wardStats.emergency.total > 0
                    ? `${wardStats.emergency.occupied} / ${wardStats.emergency.total} occupied`
                    : "No Emergency bed data"}
                </small>
              </div>

              <div className="capacity-item">
                <div className="capacity-item-header">
                  <span>Equipment</span>

                  <strong>
                    {equipmentStats.total > 0
                      ? `${Math.round(
                          (equipmentStats.occupied /
                            equipmentStats.total) *
                            100
                        )}%`
                      : "—"}
                  </strong>
                </div>

                <div className="capacity-track">
                  <div
                    className="capacity-fill normal"
                    style={{
                      width: `${
                        equipmentStats.total > 0
                          ? Math.round(
                              (equipmentStats.occupied /
                                equipmentStats.total) *
                                100
                            )
                          : 0
                      }%`,
                    }}
                  ></div>
                </div>

                <small>
                  {equipmentStats.total > 0
                    ? `${equipmentStats.occupied} active / ${equipmentStats.total} total`
                    : "No equipment data"}
                </small>
              </div>

            </div>
          </div>
        </section>

        {/* =====================================================
            BOTTLENECKS
        ===================================================== */}

        <section className="bottleneck-section">
          <div className="section-heading">
            <div>
              <span>OPERATIONAL AWARENESS</span>
              <h2>Live bottlenecks</h2>
            </div>

            <span className="updated-label">
              Based on current database state
            </span>
          </div>

          <div className="bottleneck-grid">
            {bottlenecks.map((item) => {
              const Icon = item.icon;

              return (
                <div
                  className={`bottleneck-card ${item.status}`}
                  key={item.title}
                >
                  <div className="bottleneck-icon">
                    <Icon size={19} />
                  </div>

                  <div className="bottleneck-content">
                    <div className="bottleneck-top">
                      <strong>
                        {item.title}
                      </strong>

                      <span>
                        {item.value}
                      </span>
                    </div>

                    <p>
                      {item.detail}
                    </p>
                  </div>

                  {item.status === "critical" && (
                    <AlertTriangle size={18} />
                  )}

                  {item.status === "stable" && (
                    <CheckCircle2 size={18} />
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* =====================================================
            ACTIVITY + DECISION LOOP
        ===================================================== */}

        <section className="bottom-command-grid">

          {/* EVENTS */}

          <div className="events-card">
            <div className="card-title-row">
              <div>
                <span className="section-label">
                  LIVE STATE
                </span>

                <h2>
                  Operational snapshot
                </h2>
              </div>

              <Clock3 size={19} />
            </div>

            <div className="event-list">
              {events.map((event) => {
                const Icon = event.icon;

                return (
                  <div
                    className="event-item"
                    key={event.title}
                  >
                    <div
                      className={`event-icon ${event.type}`}
                    >
                      <Icon size={15} />
                    </div>

                    <div className="event-content">
                      <strong>
                        {event.title}
                      </strong>

                      <span>
                        {event.detail}
                      </span>
                    </div>

                    <time>
                      {event.time}
                    </time>
                  </div>
                );
              })}
            </div>
          </div>

          {/* DECISION LOOP */}

          <div className="decision-card">
            <div className="card-title-row">
              <div>
                <span className="section-label">
                  DECISION LOOP
                </span>

                <h2>
                  How MedFlow AI works
                </h2>
              </div>

              <Brain size={19} />
            </div>

            <div className="decision-flow">

              <div className="decision-step active">
                <div>01</div>
                <span>Hospital State</span>
              </div>

              <ArrowRight size={15} />

              <div className="decision-step">
                <div>02</div>
                <span>Detect</span>
              </div>

              <ArrowRight size={15} />

              <div className="decision-step">
                <div>03</div>
                <span>Optimize</span>
              </div>

              <ArrowRight size={15} />

              <div className="decision-step">
                <div>04</div>
                <span>Recommend</span>
              </div>

              <ArrowRight size={15} />

              <div className="decision-step">
                <div>05</div>
                <span>Human Decision</span>
              </div>

            </div>

            <div className="human-loop-note">
              <CheckCircle2 size={16} />

              <span>
                Every AI recommendation remains under
                human operational control.
              </span>
            </div>
          </div>

        </section>

      </div>
    </main>
  );
}

export default Dashboard;
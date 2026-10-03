import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  BedDouble,
  CheckCircle2,
  Play,
  RotateCcw,
  ShieldCheck,
  Users,
} from "lucide-react";

import api from "../services/api";
import "./WhatIf.css";

const initialScenario = {
  emergency_patients: 0,
  high_priority_patients: 0,
  medium_priority_patients: 0,
  low_priority_patients: 0,

  additional_icu_beds: 0,
  additional_general_beds: 0,

  unavailable_icu_beds: 0,
  unavailable_general_beds: 0,

  unavailable_icu_staff: 0,
  unavailable_general_staff: 0,

  additional_icu_staff: 0,
  additional_general_staff: 0,

  equipment_requirements: {},
};

function WhatIf() {
  const [scenario, setScenario] = useState(initialScenario);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  /* =========================================================
     INPUT CHANGE
  ========================================================= */

  const handleChange = (event) => {
    const { name, value } = event.target;

    setScenario((previous) => ({
      ...previous,
      [name]: value === "" ? "" : Number(value),
    }));
  };

  /* =========================================================
     BUILD API PAYLOAD
  ========================================================= */

  const buildSimulationPayload = () => {
    return {
      emergency_patients: Number(
        scenario.emergency_patients || 0
      ),

      high_priority_patients: Number(
        scenario.high_priority_patients || 0
      ),

      medium_priority_patients: Number(
        scenario.medium_priority_patients || 0
      ),

      low_priority_patients: Number(
        scenario.low_priority_patients || 0
      ),

      additional_icu_beds: Number(
        scenario.additional_icu_beds || 0
      ),

      additional_general_beds: Number(
        scenario.additional_general_beds || 0
      ),

      unavailable_icu_beds: Number(
        scenario.unavailable_icu_beds || 0
      ),

      unavailable_general_beds: Number(
        scenario.unavailable_general_beds || 0
      ),

      unavailable_icu_staff: Number(
        scenario.unavailable_icu_staff || 0
      ),

      unavailable_general_staff: Number(
        scenario.unavailable_general_staff || 0
      ),

      additional_icu_staff: Number(
        scenario.additional_icu_staff || 0
      ),

      additional_general_staff: Number(
        scenario.additional_general_staff || 0
      ),

      equipment_requirements:
        scenario.equipment_requirements || {},
    };
  };

  /* =========================================================
     RUN SIMULATION
  ========================================================= */

  const runSimulation = async () => {
    try {
      setLoading(true);
      setError("");
      setResult(null);

      const payload = buildSimulationPayload();

      console.log(
        "What-If Simulation Payload:",
        payload
      );

      const response = await api.post(
        "/what-if/simulate",
        payload
      );

      setResult(response.data);
    } catch (err) {
      console.error(
        "What-If simulation failed:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to run simulation."
      );
    } finally {
      setLoading(false);
    }
  };

  /* =========================================================
     RESET
  ========================================================= */

  const resetScenario = () => {
    setScenario({
      ...initialScenario,
      equipment_requirements: {},
    });

    setResult(null);
    setError("");
  };

  /* =========================================================
     FORMAT RESULT LABEL
  ========================================================= */

  const formatLabel = (key) => {
    return key
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (letter) => letter.toUpperCase()
      );
  };

  /* =========================================================
     FORMAT RESULT VALUE
  ========================================================= */

  const renderValue = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    if (typeof value === "object") {
      return JSON.stringify(value);
    }

    return String(value);
  };

  /* =========================================================
     RESULT ROW
  ========================================================= */

  const ResultRow = ({ label, value }) => (
    <div className="what-if-result-row">
      <span>{label}</span>
      <strong>{renderValue(value)}</strong>
    </div>
  );

  /* =========================================================
     OBJECT ROWS
  ========================================================= */

  const renderObjectRows = (object) => {
    if (
      !object ||
      typeof object !== "object" ||
      Array.isArray(object)
    ) {
      return null;
    }

    return Object.entries(object).map(
      ([key, value]) => (
        <ResultRow
          key={key}
          label={formatLabel(key)}
          value={value}
        />
      )
    );
  };

  /* =========================================================
     CAPACITY CARD
  ========================================================= */

  const renderCapacity = () => {
    if (
      !result?.initial_capacity ||
      !result?.final_capacity
    ) {
      return null;
    }

    const departments = Object.keys(
      result.initial_capacity
    );

    return (
      <ResultCard
        title="Hospital Capacity"
        description="Initial and final simulated bed capacity."
        icon={<BedDouble size={18} />}
      >
        {departments.map((department) => {
          const initial =
            result.initial_capacity[department];

          const final =
            result.final_capacity[department];

          return (
            <div
              className="what-if-result-row"
              key={department}
            >
              <span>
                {formatLabel(department)}
              </span>

              <strong>
                {initial?.available_beds ?? 0} →{" "}
                {final?.available_beds ?? 0} available
              </strong>
            </div>
          );
        })}
      </ResultCard>
    );
  };

  /* =========================================================
     BOTTLENECKS
  ========================================================= */

  const renderBottlenecks = () => {
    if (!result?.bottlenecks) {
      return null;
    }

    if (result.bottlenecks.length === 0) {
      return (
        <ResultCard
          title="Detected Bottlenecks"
          description="Operational constraints identified by the simulation."
          icon={<AlertTriangle size={18} />}
        >
          <ResultRow
            label="Status"
            value="No bottlenecks detected"
          />
        </ResultCard>
      );
    }

    return (
      <ResultCard
        title="Detected Bottlenecks"
        description="Operational constraints identified by the simulation."
        icon={<AlertTriangle size={18} />}
      >
        {result.bottlenecks.map(
          (bottleneck, index) => (
            <div
              className="what-if-result-row"
              key={index}
            >
              <span>
                {formatLabel(
                  bottleneck.type ||
                    bottleneck.resource ||
                    `Bottleneck ${index + 1}`
                )}
              </span>

              <strong>
                {renderValue(
                  bottleneck.reason ||
                    bottleneck.message ||
                    bottleneck
                )}
              </strong>
            </div>
          )
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     STAFF RECOMMENDATIONS
  ========================================================= */

  const renderStaffRecommendations = () => {
    if (
      !result?.staff_recommendations
    ) {
      return null;
    }

    return (
      <ResultCard
        title="Staff Recommendations"
        description="Staff assignments selected for the simulated scenario."
        icon={<Users size={18} />}
      >
        {result.staff_recommendations.length ===
        0 ? (
          <ResultRow
            label="Status"
            value="No staff recommendation required"
          />
        ) : (
          result.staff_recommendations.map(
            (item, index) => (
              <div key={index}>
                <ResultRow
                  label="Patient"
                  value={item.patient_id}
                />

                <ResultRow
                  label="Emergency Level"
                  value={item.emergency_level}
                />

                <ResultRow
                  label="Department"
                  value={item.department}
                />

                <ResultRow
                  label="Recommended Staff"
                  value={`${item.recommended_staff_id || "—"}${
                    item.staff_name
                      ? ` — ${item.staff_name}`
                      : ""
                  }`}
                />

                <ResultRow
                  label="Role"
                  value={item.staff_role}
                />

                <ResultRow
                  label="Action"
                  value={item.recommended_action}
                />

                <ResultRow
                  label="Optimization Score"
                  value={item.optimization_score}
                />

                <ResultRow
                  label="Reason"
                  value={item.reason}
                />

                <ResultRow
                  label="Expected Impact"
                  value={item.expected_impact}
                />

                <ResultRow
                  label="Human Decision Required"
                  value={
                    item.human_decision_required
                      ? "Yes"
                      : "No"
                  }
                />

                {index <
                  result.staff_recommendations
                    .length -
                    1 && (
                  <hr />
                )}
              </div>
            )
          )
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     STAFF OPTIMIZATION
  ========================================================= */

  const renderStaffOptimization = () => {
    if (!result?.staff_optimization) {
      return null;
    }

    return (
      <ResultCard
        title="Staff Optimization"
        description="OR-Tools staff allocation result."
        icon={<Users size={18} />}
      >
        <ResultRow
          label="Status"
          value={
            result.staff_optimization.status
          }
        />

        {result.staff_optimization
          .allocations?.length > 0 && (
          <>
            <ResultRow
              label="Allocations"
              value={
                result.staff_optimization
                  .allocations.length
              }
            />

            {result.staff_optimization.allocations.map(
              (allocation, index) => (
                <ResultRow
                  key={index}
                  label={`Allocation ${index + 1}`}
                  value={`${allocation.patient_id} → ${allocation.staff_id}`}
                />
              )
            )}
          </>
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     EQUIPMENT
  ========================================================= */

  const renderEquipment = () => {
    if (
      !result?.equipment_recommendations &&
      !result?.equipment_optimization
    ) {
      return null;
    }

    return (
      <ResultCard
        title="Equipment Feasibility"
        description="Simulated equipment availability and allocation."
        icon={<Activity size={18} />}
      >
        {result.equipment_optimization && (
          <>
            <ResultRow
              label="Optimization Status"
              value={
                result.equipment_optimization
                  .status
              }
            />

            <ResultRow
              label="Objective Value"
              value={
                result.equipment_optimization
                  .objective_value
              }
            />
          </>
        )}

        {result.equipment_recommendations?.length ===
        0 ? (
          <ResultRow
            label="Recommendations"
            value="No equipment allocation required"
          />
        ) : (
          result.equipment_recommendations.map(
            (item, index) => (
              <div key={index}>
                <ResultRow
                  label="Patient"
                  value={item.patient_id}
                />

                <ResultRow
                  label="Equipment"
                  value={
                    item.recommended_equipment_id
                  }
                />

                <ResultRow
                  label="Action"
                  value={
                    item.recommended_action
                  }
                />

                <ResultRow
                  label="Reason"
                  value={item.reason}
                />
              </div>
            )
          )
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     PERSONALIZED RECOMMENDATIONS
  ========================================================= */

  const renderPersonalizedRecommendations = () => {
    if (
      !result?.personalized_recommendations
    ) {
      return null;
    }

    return (
      <ResultCard
        title="Personalized Recommendations"
        description="Patient-level operational recommendations generated by the simulation."
        icon={<CheckCircle2 size={18} />}
      >
        {result.personalized_recommendations.length ===
        0 ? (
          <ResultRow
            label="Status"
            value="No personalized recommendation required"
          />
        ) : (
          result.personalized_recommendations.map(
            (item, index) => (
              <div key={index}>
                <ResultRow
                  label="Patient"
                  value={item.patient_id}
                />

                <ResultRow
                  label="Emergency Level"
                  value={item.emergency_level}
                />

                <ResultRow
                  label="Department"
                  value={item.department}
                />

                <ResultRow
                  label="Action"
                  value={item.recommended_action}
                />

                <ResultRow
                  label="Recommended Bed"
                  value={item.recommended_bed_id}
                />

                <ResultRow
                  label="Affected Patient"
                  value={item.affected_patient_id}
                />

                <ResultRow
                  label="Current Bed"
                  value={
                    item.affected_patient_current_bed
                  }
                />

                <ResultRow
                  label="Replacement Bed"
                  value={
                    item.affected_patient_replacement_bed
                  }
                />

                <ResultRow
                  label="Reason"
                  value={item.reason}
                />

                <ResultRow
                  label="Expected Impact"
                  value={item.expected_impact}
                />

                <ResultRow
                  label="Human Decision Required"
                  value={
                    item.human_decision_required
                      ? "Yes"
                      : "No"
                  }
                />

                {index <
                  result.personalized_recommendations
                    .length -
                    1 && (
                  <hr />
                )}
              </div>
            )
          )
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     UNIFIED RECOMMENDATIONS
  ========================================================= */

  const renderUnifiedRecommendations = () => {
    if (
      !result?.unified_recommendations
    ) {
      return null;
    }

    return (
      <ResultCard
        title="Unified Recommendations"
        description="Combined bed, staff, and equipment recommendation for each simulated patient."
        icon={<Activity size={18} />}
        highlighted
      >
        {result.unified_recommendations.length ===
        0 ? (
          <ResultRow
            label="Status"
            value="No unified recommendation generated"
          />
        ) : (
          result.unified_recommendations.map(
            (item, index) => (
              <div key={index}>
                <ResultRow
                  label="Patient"
                  value={item.patient_id}
                />

                <ResultRow
                  label="Emergency Level"
                  value={item.emergency_level}
                />

                <ResultRow
                  label="Department"
                  value={item.department}
                />

                <ResultRow
                  label="Recommended Action"
                  value={item.recommended_action}
                />

                <ResultRow
                  label="Primary Bottleneck"
                  value={item.primary_bottleneck}
                />

                <ResultRow
                  label="Bed"
                  value={
                    item.resources?.bed
                      ? `${item.resources.bed.status} — ${
                          item.resources.bed
                            .recommended_bed_id ||
                          "No bed"
                        }`
                      : "—"
                  }
                />

                <ResultRow
                  label="Staff"
                  value={
                    item.resources?.staff
                      ? `${item.resources.staff.status} — ${
                          item.resources.staff
                            .recommended_staff_id ||
                          "No staff"
                        }`
                      : "—"
                  }
                />

                <ResultRow
                  label="Equipment"
                  value={
                    item.resources?.equipment
                      ? `${item.resources.equipment.status} — ${
                          item.resources.equipment
                            .recommended_equipment_id ||
                          "None"
                        }`
                      : "—"
                  }
                />

                <ResultRow
                  label="Reason"
                  value={item.reason}
                />

                <ResultRow
                  label="Expected Impact"
                  value={item.expected_impact}
                />

                <ResultRow
                  label="Human Decision Required"
                  value={
                    item.human_decision_required
                      ? "Yes"
                      : "No"
                  }
                />

                {index <
                  result.unified_recommendations
                    .length -
                    1 && (
                  <hr />
                )}
              </div>
            )
          )
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     OPTIMIZATION
  ========================================================= */

  const renderOptimization = () => {
    if (!result?.optimization) {
      return null;
    }

    return (
      <ResultCard
        title="Optimization"
        description="OR-Tools optimization result."
        icon={<Activity size={18} />}
      >
        {renderObjectRows(
          result.optimization
        )}
      </ResultCard>
    );
  };

  /* =========================================================
     RENDER
  ========================================================= */

  return (
    <main className="what-if-page">
      <div className="what-if-container">

        {/* HEADER */}

        <section className="what-if-header">
          <div>
            <div className="what-if-eyebrow">
              <Activity size={15} />

              <span>
                SCENARIO SIMULATION
              </span>
            </div>

            <h1>
              What-If Simulation
            </h1>

            <p>
              Test hypothetical hospital
              scenarios without changing the
              live database.
            </p>
          </div>

          <div className="simulation-safe-badge">
            <ShieldCheck size={17} />

            <span>
              Simulation Only
            </span>
          </div>
        </section>

        {/* SCENARIO BUILDER */}

        <section className="scenario-card">

          <div className="scenario-card-header">
            <span className="section-label">
              SCENARIO BUILDER
            </span>

            <h2>
              Define a hypothetical situation
            </h2>

            <p>
              Adjust patient demand, bed capacity,
              and staff availability to see how
              hospital operations would respond.
            </p>
          </div>

          {/* PATIENT DEMAND */}

          <div className="scenario-section">
            <div className="scenario-section-header">

              <div className="scenario-section-icon blue">
                <Users size={18} />
              </div>

              <div>
                <h3>
                  Patient Demand
                </h3>

                <p>
                  Simulate additional incoming
                  patients by priority.
                </p>
              </div>
            </div>

            <div className="scenario-grid">

              <InputField
                label="Emergency Patients"
                name="emergency_patients"
                value={
                  scenario.emergency_patients
                }
                onChange={handleChange}
              />

              <InputField
                label="High Priority Patients"
                name="high_priority_patients"
                value={
                  scenario.high_priority_patients
                }
                onChange={handleChange}
              />

              <InputField
                label="Medium Priority Patients"
                name="medium_priority_patients"
                value={
                  scenario.medium_priority_patients
                }
                onChange={handleChange}
              />

              <InputField
                label="Low Priority Patients"
                name="low_priority_patients"
                value={
                  scenario.low_priority_patients
                }
                onChange={handleChange}
              />

            </div>
          </div>

          {/* BED CAPACITY */}

          <div className="scenario-section">
            <div className="scenario-section-header">

              <div className="scenario-section-icon green">
                <BedDouble size={18} />
              </div>

              <div>
                <h3>
                  Bed Capacity
                </h3>

                <p>
                  Add capacity or simulate
                  temporarily unavailable beds.
                </p>
              </div>
            </div>

            <div className="scenario-grid">

              <InputField
                label="Additional ICU Beds"
                name="additional_icu_beds"
                value={
                  scenario.additional_icu_beds
                }
                onChange={handleChange}
              />

              <InputField
                label="Additional General Beds"
                name="additional_general_beds"
                value={
                  scenario.additional_general_beds
                }
                onChange={handleChange}
              />

              <InputField
                label="Unavailable ICU Beds"
                name="unavailable_icu_beds"
                value={
                  scenario.unavailable_icu_beds
                }
                onChange={handleChange}
              />

              <InputField
                label="Unavailable General Beds"
                name="unavailable_general_beds"
                value={
                  scenario.unavailable_general_beds
                }
                onChange={handleChange}
              />

            </div>
          </div>

          {/* STAFF CAPACITY */}

          <div className="scenario-section">
            <div className="scenario-section-header">

              <div className="scenario-section-icon purple">
                <Users size={18} />
              </div>

              <div>
                <h3>
                  Staff Capacity
                </h3>

                <p>
                  Simulate staff shortages or
                  additional operational staff.
                </p>
              </div>
            </div>

            <div className="scenario-grid">

              <InputField
                label="Unavailable ICU Staff"
                name="unavailable_icu_staff"
                value={
                  scenario.unavailable_icu_staff
                }
                onChange={handleChange}
              />

              <InputField
                label="Unavailable General Staff"
                name="unavailable_general_staff"
                value={
                  scenario.unavailable_general_staff
                }
                onChange={handleChange}
              />

              <InputField
                label="Additional ICU Staff"
                name="additional_icu_staff"
                value={
                  scenario.additional_icu_staff
                }
                onChange={handleChange}
              />

              <InputField
                label="Additional General Staff"
                name="additional_general_staff"
                value={
                  scenario.additional_general_staff
                }
                onChange={handleChange}
              />

            </div>
          </div>

          {/* ACTIONS */}

          <div className="scenario-actions">

            <button
              type="button"
              className="what-if-secondary-button"
              onClick={resetScenario}
              disabled={loading}
            >
              <RotateCcw size={16} />
              Reset
            </button>

            <button
              type="button"
              className="what-if-primary-button"
              onClick={runSimulation}
              disabled={loading}
            >
              <Play size={16} />

              {loading
                ? "Running Simulation..."
                : "Run Simulation"}
            </button>

          </div>

          {/* ERROR */}

          {error && (
            <div className="what-if-error">
              <AlertTriangle size={17} />

              <span>
                {error}
              </span>
            </div>
          )}

        </section>

        {/* RESULTS */}

        {result && (
          <section className="simulation-results">

            <div className="results-header">

              <div>
                <div className="what-if-eyebrow">
                  <CheckCircle2 size={15} />

                  <span>
                    SIMULATION RESULT
                  </span>
                </div>

                <h2>
                  Scenario Analysis
                </h2>

                <p>
                  The following results describe
                  the simulated hospital state.
                </p>
              </div>

              <div className="database-safe-badge">
                <ShieldCheck size={16} />

                <span>
                  Database unchanged
                </span>
              </div>

            </div>

            {/* DATABASE STATUS */}

            <div className="simulation-status-card">

              <div className="simulation-status-icon">
                <ShieldCheck size={20} />
              </div>

              <div>
                <span>
                  DATABASE MODIFIED
                </span>

                <strong>
                  {result.database_modified
                    ? "Yes"
                    : "No"}
                </strong>

                <p>
                  What-If simulation is designed
                  to evaluate scenarios without
                  committing hypothetical changes.
                </p>
              </div>

            </div>

            {/* CAPACITY */}

            {renderCapacity()}

            {/* BOTTLENECKS */}

            {renderBottlenecks()}

            {/* STAFF */}

            {renderStaffRecommendations()}

            {renderStaffOptimization()}

            {/* EQUIPMENT */}

            {renderEquipment()}

            {/* PERSONALIZED */}

            {renderPersonalizedRecommendations()}

            {/* UNIFIED */}

            {renderUnifiedRecommendations()}

            {/* OPTIMIZATION */}

            {renderOptimization()}

            {/* SIMULATED DEMAND */}

            {result.simulated_demand && (
              <ResultCard
                title="Simulated Demand"
                description="Additional patient demand introduced by the scenario."
                icon={<Users size={18} />}
              >
                {renderObjectRows(
                  result.simulated_demand
                )}
              </ResultCard>
            )}

            {/* REALLOCATION CANDIDATES */}

            {result.reallocation_candidates && (
              <ResultCard
                title="Reallocation Candidates"
                description="Existing patients that can be considered for simulated reallocation."
                icon={<BedDouble size={18} />}
              >
                {result.reallocation_candidates.length ===
                0 ? (
                  <ResultRow
                    label="Status"
                    value="No reallocation candidates"
                  />
                ) : (
                  result.reallocation_candidates.map(
                    (item, index) => (
                      <div key={index}>
                        <ResultRow
                          label="Patient"
                          value={item.patient_id}
                        />

                        <ResultRow
                          label="Emergency Level"
                          value={
                            item.emergency_level
                          }
                        />

                        <ResultRow
                          label="Current Bed"
                          value={
                            item.current_bed_id
                          }
                        />

                        <ResultRow
                          label="Current Ward"
                          value={
                            item.current_ward
                          }
                        />
                      </div>
                    )
                  )
                )}
              </ResultCard>
            )}

            {/* RAW RESPONSE */}

            <details className="raw-response">

              <summary>
                View complete simulation response
              </summary>

              <pre>
                {JSON.stringify(
                  result,
                  null,
                  2
                )}
              </pre>

            </details>

          </section>
        )}

      </div>
    </main>
  );
}

/* =========================================================
   INPUT FIELD
========================================================= */

function InputField({
  label,
  name,
  value,
  onChange,
}) {
  return (
    <label className="scenario-input-group">

      <span>
        {label}
      </span>

      <input
        type="number"
        min="0"
        name={name}
        value={value}
        onChange={onChange}
      />

    </label>
  );
}

/* =========================================================
   RESULT CARD
========================================================= */

function ResultCard({
  title,
  description,
  icon,
  children,
  highlighted = false,
}) {
  return (
    <div
      className={`result-card ${
        highlighted
          ? "result-card-highlighted"
          : ""
      }`}
    >

      <div className="result-card-header">

        <div className="result-card-icon">
          {icon}
        </div>

        <div>

          <h3>
            {title}
          </h3>

          <p>
            {description}
          </p>

        </div>

      </div>

      <div className="result-card-body">
        {children}
      </div>

    </div>
  );
}

export default WhatIf;
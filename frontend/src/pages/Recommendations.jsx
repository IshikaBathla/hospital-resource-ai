import { useEffect, useState } from "react";
import {
  Lightbulb,
  RefreshCw,
  CheckCircle2,
  Clock3,
  UserRoundCheck,
  BedDouble,
  UserRound,
  Microscope,
  XCircle,
  Pencil,
  X,
  History,
} from "lucide-react";

import api from "../services/api";
import "./Recommendations.css";

function Recommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [decisionHistory, setDecisionHistory] = useState([]);

  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [success, setSuccess] = useState("");

  const [processingId, setProcessingId] = useState(null);

  const [modifyRecommendation, setModifyRecommendation] =
    useState(null);

  const [modifyForm, setModifyForm] = useState({
    modified_bed_id: "",
    modified_staff_id: "",
    modified_equipment_id: "",
    reason: "",
  });

  // =========================================================
  // FETCH PENDING RECOMMENDATIONS
  // =========================================================

  const fetchRecommendations = async (showRefresh = false) => {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const response = await api.get(
        "/recommendations/pending"
      );

      setRecommendations(
        Array.isArray(response.data)
          ? response.data
          : []
      );
    } catch (err) {
      console.error(
        "Failed to fetch recommendations:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to load recommendations."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // =========================================================
  // FETCH DECISION HISTORY
  // =========================================================

  const fetchDecisionHistory = async () => {
    try {
      setHistoryLoading(true);
      setHistoryError("");

      /*
       * Currently P106 has a verified decision history.
       * We use the patient-specific endpoint and keep the
       * existing backend API unchanged.
       */
      const response = await api.get(
        "/recommendations/patient/P106/decision-history"
      );

      setDecisionHistory(
        Array.isArray(response.data)
          ? response.data
          : []
      );
    } catch (err) {
      console.error(
        "Failed to fetch decision history:",
        err
      );

      setHistoryError(
        err?.response?.data?.detail ||
          "Unable to load decision history."
      );
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
    fetchDecisionHistory();
  }, []);

  // =========================================================
  // APPROVE
  // =========================================================

  const approveRecommendation = async (
    recommendationId
  ) => {
    try {
      setProcessingId(recommendationId);
      setError("");
      setSuccess("");

      await api.post(
        `/recommendations/${recommendationId}/approve`
      );

      setSuccess(
        "Recommendation approved successfully."
      );

      await fetchRecommendations(true);
      await fetchDecisionHistory();
    } catch (err) {
      console.error(
        "Failed to approve recommendation:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to approve recommendation."
      );
    } finally {
      setProcessingId(null);
    }
  };

  // =========================================================
  // REJECT
  // =========================================================

  const rejectRecommendation = async (
    recommendationId
  ) => {
    try {
      setProcessingId(recommendationId);
      setError("");
      setSuccess("");

      await api.post(
        `/recommendations/${recommendationId}/reject`
      );

      setSuccess(
        "Recommendation rejected successfully."
      );

      await fetchRecommendations(true);
      await fetchDecisionHistory();
    } catch (err) {
      console.error(
        "Failed to reject recommendation:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to reject recommendation."
      );
    } finally {
      setProcessingId(null);
    }
  };

  // =========================================================
  // MODIFY
  // =========================================================

  const openModifyModal = (recommendation) => {
    setError("");
    setSuccess("");

    setModifyRecommendation(recommendation);

    setModifyForm({
      modified_bed_id:
        recommendation.recommended_bed_id || "",

      modified_staff_id:
        recommendation.recommended_staff_id || "",

      modified_equipment_id:
        recommendation.recommended_equipment_id || "",

      reason: "",
    });
  };

  const closeModifyModal = () => {
    setModifyRecommendation(null);

    setModifyForm({
      modified_bed_id: "",
      modified_staff_id: "",
      modified_equipment_id: "",
      reason: "",
    });
  };

  const handleModifyChange = (event) => {
    const { name, value } = event.target;

    setModifyForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const submitModification = async (event) => {
    event.preventDefault();

    if (!modifyRecommendation) {
      return;
    }

    try {
      setProcessingId(
        modifyRecommendation.recommendation_id
      );

      setError("");
      setSuccess("");

      await api.post(
        `/recommendations/${modifyRecommendation.recommendation_id}/modify`,
        {
          modified_bed_id:
            modifyForm.modified_bed_id.trim() || null,

          modified_staff_id:
            modifyForm.modified_staff_id.trim() || null,

          modified_equipment_id:
            modifyForm.modified_equipment_id.trim() ||
            null,

          reason:
            modifyForm.reason.trim() || null,
        }
      );

      closeModifyModal();

      setSuccess(
        "Recommendation modified successfully."
      );

      await fetchRecommendations(true);
      await fetchDecisionHistory();
    } catch (err) {
      console.error(
        "Failed to modify recommendation:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          "Unable to modify recommendation."
      );
    } finally {
      setProcessingId(null);
    }
  };

  // =========================================================
  // FORMAT DATE
  // =========================================================

  const formatDecisionDate = (dateValue) => {
    if (!dateValue) {
      return "Not available";
    }

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
      return dateValue;
    }

    return date.toLocaleString();
  };

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <main className="recommendations-page">
      <div className="recommendations-content">

        {/* =================================================
            HEADER
        ================================================= */}

        <section className="recommendations-header">

          <div>
            <div className="recommendations-eyebrow">
              <Lightbulb size={15} />
              <span>AI OPERATIONS</span>
            </div>

            <h1>Recommendations</h1>

            <p>
              Review AI-generated resource allocation
              recommendations and make the final human
              decision.
            </p>
          </div>

          <button
            className="recommendations-refresh"
            onClick={async () => {
              await fetchRecommendations(true);
              await fetchDecisionHistory();
            }}
            disabled={refreshing}
          >
            <RefreshCw
              size={17}
              className={refreshing ? "spin" : ""}
            />

            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>

        </section>

        {/* =================================================
            SUMMARY
        ================================================= */}

        <section className="recommendation-stats">

          <div className="recommendation-stat-card">

            <div className="recommendation-stat-icon amber">
              <Clock3 size={19} />
            </div>

            <div>
              <span>Pending Decisions</span>

              <strong>
                {recommendations.length}
              </strong>
            </div>

          </div>

          <div className="recommendation-stat-card">

            <div className="recommendation-stat-icon green">
              <UserRoundCheck size={19} />
            </div>

            <div>
              <span>Human Review</span>

              <strong>
                {recommendations.length > 0
                  ? "Required"
                  : "Clear"}
              </strong>
            </div>

          </div>

          <div className="recommendation-stat-card">

            <div className="recommendation-stat-icon blue">
              <Lightbulb size={19} />
            </div>

            <div>
              <span>Decision Model</span>

              <strong>
                AI + Human
              </strong>
            </div>

          </div>

        </section>

        {/* =================================================
            ERROR
        ================================================= */}

        {error && (
          <div className="recommendations-error">
            {error}
          </div>
        )}

        {/* =================================================
            SUCCESS
        ================================================= */}

        {success && (
          <div className="recommendations-success">

            <CheckCircle2 size={16} />

            <span>
              {success}
            </span>

          </div>
        )}

        {/* =================================================
            PENDING RECOMMENDATIONS
        ================================================= */}

        <section className="recommendations-section">

          <div className="recommendations-section-heading">

            <div>

              <span>
                HUMAN-IN-THE-LOOP
              </span>

              <h2>
                Pending recommendations
              </h2>

            </div>

            {recommendations.length > 0 && (
              <span className="pending-count">
                {recommendations.length} pending
              </span>
            )}

          </div>

          {/* LOADING */}

          {loading ? (

            <div className="recommendations-empty">

              <Clock3 size={30} />

              <h3>
                Loading recommendations
              </h3>

              <p>
                Fetching the latest operational
                recommendations.
              </p>

            </div>

          ) : recommendations.length === 0 ? (

            /* EMPTY */

            <div className="recommendations-empty">

              <div className="empty-check">
                <CheckCircle2 size={28} />
              </div>

              <h3>
                No pending recommendations
              </h3>

              <p>
                The system currently has no
                recommendations waiting for human
                review.
              </p>

            </div>

          ) : (

            /* CARDS */

            <div className="recommendation-list">

              {recommendations.map((recommendation) => {

                const isProcessing =
                  processingId ===
                  recommendation.recommendation_id;

                return (
                  <article
                    className="recommendation-card"
                    key={
                      recommendation.recommendation_id
                    }
                  >

                    <div className="recommendation-card-top">

                      <div>

                        <span className="recommendation-type">
                          {recommendation.recommendation_type ||
                            "Resource Allocation"}
                        </span>

                        <h3>
                          Patient{" "}
                          {recommendation.patient_id}
                        </h3>

                      </div>

                      <span className="pending-pill">
                        Pending Review
                      </span>

                    </div>

                    {/* RESOURCES */}

                    <div className="recommended-resources">

                      <div className="recommended-resource">

                        <BedDouble size={18} />

                        <div>

                          <span>
                            Recommended Bed
                          </span>

                          <strong>
                            {recommendation.recommended_bed_id ||
                              "Not specified"}
                          </strong>

                        </div>

                      </div>

                      <div className="recommended-resource">

                        <UserRound size={18} />

                        <div>

                          <span>
                            Recommended Staff
                          </span>

                          <strong>
                            {recommendation.recommended_staff_id ||
                              "Not specified"}
                          </strong>

                        </div>

                      </div>

                      <div className="recommended-resource">

                        <Microscope size={18} />

                        <div>

                          <span>
                            Equipment
                          </span>

                          <strong>
                            {recommendation.recommended_equipment_id ||
                              "Not specified"}
                          </strong>

                        </div>

                      </div>

                    </div>

                    {/* REASON */}

                    <div className="recommendation-reason">

                      <span>
                        WHY THIS ACTION
                      </span>

                      <p>
                        {recommendation.reason ||
                          "No explanation provided."}
                      </p>

                    </div>

                    {/* ACTIONS */}

                    <div className="recommendation-actions">

                      <button
                        className="reject-button"
                        type="button"
                        disabled={isProcessing}
                        onClick={() =>
                          rejectRecommendation(
                            recommendation.recommendation_id
                          )
                        }
                      >

                        <XCircle size={15} />

                        {isProcessing
                          ? "Processing..."
                          : "Reject"}

                      </button>

                      <button
                        className="modify-button"
                        type="button"
                        disabled={isProcessing}
                        onClick={() =>
                          openModifyModal(
                            recommendation
                          )
                        }
                      >

                        <Pencil size={15} />

                        Modify

                      </button>

                      <button
                        className="approve-button"
                        type="button"
                        disabled={isProcessing}
                        onClick={() =>
                          approveRecommendation(
                            recommendation.recommendation_id
                          )
                        }
                      >

                        <CheckCircle2 size={15} />

                        {isProcessing
                          ? "Processing..."
                          : "Approve"}

                      </button>

                    </div>

                  </article>
                );
              })}

            </div>
          )}

        </section>

        {/* =================================================
            DECISION HISTORY
        ================================================= */}

        <section className="recommendations-section decision-history-section">

          <div className="recommendations-section-heading">

            <div>

              <span>
                AUDIT TRAIL
              </span>

              <h2>
                Decision History
              </h2>

            </div>

            <div className="decision-history-heading-icon">
              <History size={19} />
            </div>

          </div>

          {historyError && (
            <div className="recommendations-error">
              {historyError}
            </div>
          )}

          {historyLoading ? (

            <div className="recommendations-empty">

              <Clock3 size={30} />

              <h3>
                Loading decision history
              </h3>

              <p>
                Fetching previously recorded human decisions.
              </p>

            </div>

          ) : decisionHistory.length === 0 ? (

            <div className="recommendations-empty">

              <History size={30} />

              <h3>
                No decision history
              </h3>

              <p>
                No human decisions have been recorded yet.
              </p>

            </div>

          ) : (

            <div className="decision-history-list">

              {decisionHistory.map((decision) => (

                <article
                  className="decision-history-card"
                  key={decision.decision_id}
                >

                  <div className="decision-history-main">

                    <div className="decision-history-icon">
                      <History size={18} />
                    </div>

                    <div>

                      <span className="decision-history-label">
                        Patient
                      </span>

                      <strong>
                        {decision.patient_id}
                      </strong>

                    </div>

                  </div>

                  <div className="decision-history-field">

                    <span>
                      Decision
                    </span>

                    <strong
                      className={`decision-badge ${
                        decision.decision || ""
                      }`}
                    >
                      {decision.decision || "Unknown"}
                    </strong>

                  </div>

                  <div className="decision-history-field">

                    <span>
                      Recommended Bed
                    </span>

                    <strong>
                      {decision.recommended_bed_id ||
                        "Not specified"}
                    </strong>

                  </div>

                  <div className="decision-history-field">

                    <span>
                      Modified Bed
                    </span>

                    <strong>
                      {decision.modified_bed_id ||
                        "—"}
                    </strong>

                  </div>

                  <div className="decision-history-field decision-history-reason">

                    <span>
                      Reason
                    </span>

                    <strong>
                      {decision.reason ||
                        "No reason recorded"}
                    </strong>

                  </div>

                  <div className="decision-history-field">

                    <span>
                      Decision Time
                    </span>

                    <strong>
                      {formatDecisionDate(
                        decision.created_at
                      )}
                    </strong>

                  </div>

                </article>

              ))}

            </div>

          )}

        </section>

      </div>

      {/* ===================================================
          MODIFY MODAL
      =================================================== */}

      {modifyRecommendation && (

        <div
          className="modify-modal-overlay"
          onMouseDown={(event) => {

            if (
              event.target === event.currentTarget &&
              !processingId
            ) {
              closeModifyModal();
            }

          }}
        >

          <div className="modify-modal">

            <div className="modify-modal-header">

              <div>

                <span>
                  HUMAN OVERRIDE
                </span>

                <h2>
                  Modify Recommendation
                </h2>

                <p>
                  Patient{" "}
                  {modifyRecommendation.patient_id}
                </p>

              </div>

              <button
                type="button"
                className="modify-close-button"
                onClick={closeModifyModal}
                disabled={!!processingId}
              >
                <X size={18} />
              </button>

            </div>

            <form onSubmit={submitModification}>

              <div className="modify-form-grid">

                <label>

                  <span>
                    Bed ID
                  </span>

                  <input
                    type="text"
                    name="modified_bed_id"
                    value={
                      modifyForm.modified_bed_id
                    }
                    onChange={handleModifyChange}
                    placeholder="e.g. B101"
                  />

                </label>

                <label>

                  <span>
                    Staff ID
                  </span>

                  <input
                    type="text"
                    name="modified_staff_id"
                    value={
                      modifyForm.modified_staff_id
                    }
                    onChange={handleModifyChange}
                    placeholder="e.g. S101"
                  />

                </label>

                <label>

                  <span>
                    Equipment ID
                  </span>

                  <input
                    type="text"
                    name="modified_equipment_id"
                    value={
                      modifyForm.modified_equipment_id
                    }
                    onChange={handleModifyChange}
                    placeholder="e.g. E201"
                  />

                </label>

                <label className="modify-reason-field">

                  <span>
                    Reason for modification
                  </span>

                  <textarea
                    name="reason"
                    value={modifyForm.reason}
                    onChange={handleModifyChange}
                    placeholder="Explain why the recommendation is being changed..."
                    rows={4}
                  />

                </label>

              </div>

              <div className="modify-modal-actions">

                <button
                  type="button"
                  className="modify-cancel-button"
                  onClick={closeModifyModal}
                  disabled={!!processingId}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="modify-submit-button"
                  disabled={
                    !!processingId ||
                    (
                      !modifyForm.modified_bed_id.trim() &&
                      !modifyForm.modified_staff_id.trim() &&
                      !modifyForm.modified_equipment_id.trim()
                    )
                  }
                >

                  <CheckCircle2 size={15} />

                  {processingId
                    ? "Saving..."
                    : "Save Modification"}

                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </main>
  );
}

export default Recommendations;
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BedDouble,
  Users,
  Cpu,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

import api from "../services/api";
import "./Resources.css";

function Resources() {
  const [beds, setBeds] = useState([]);
  const [staff, setStaff] = useState([]);
  const [equipment, setEquipment] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadResources();
  }, []);

  const loadResources = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const [
        bedsResponse,
        staffResponse,
        equipmentResponse,
      ] = await Promise.all([
        api.get("/beds"),
        api.get("/staff"),
        api.get("/equipment"),
      ]);

      setBeds(bedsResponse.data || []);
      setStaff(staffResponse.data || []);
      setEquipment(equipmentResponse.data || []);
    } catch (err) {
      console.error("Resource loading failed:", err);

      setError(
        err?.response?.data?.detail ||
          "Unable to load hospital resource data."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /* =========================================================
     RESOURCE STATS
  ========================================================= */

  const bedStats = useMemo(() => {
    const total = beds.length;

    const available = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "available"
    ).length;

    const occupied = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "occupied"
    ).length;

    const maintenance = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "maintenance"
    ).length;

    const turnover = beds.filter(
      (bed) =>
        String(bed.status).toLowerCase() ===
        "turnover_required"
    ).length;

    return {
      total,
      available,
      occupied,
      maintenance,
      turnover,
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
      (member) => {
        const status = String(
          member.status
        ).toLowerCase();

        return (
          status === "busy" ||
          status === "assigned"
        );
      }
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
      (item) => {
        const status = String(
          item.status
        ).toLowerCase();

        return (
          status === "occupied" ||
          status === "assigned"
        );
      }
    ).length;

    const maintenance = equipment.filter(
      (item) =>
        String(item.status).toLowerCase() ===
        "maintenance"
    ).length;

    return {
      total,
      available,
      occupied,
      maintenance,
    };
  }, [equipment]);

  /* =========================================================
     HELPERS
  ========================================================= */

  const formatStatus = (status) => {
    if (!status) {
      return "—";
    }

    return String(status)
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      );
  };

  const statusClass = (status) => {
    const normalized = String(
      status || ""
    ).toLowerCase();

    if (normalized === "available") {
      return "status-available";
    }

    if (
      normalized === "occupied" ||
      normalized === "assigned"
    ) {
      return "status-occupied";
    }

    if (
      normalized === "maintenance" ||
      normalized === "turnover_required"
    ) {
      return "status-warning";
    }

    if (
      normalized === "busy"
    ) {
      return "status-busy";
    }

    return "status-default";
  };

  /* =========================================================
     LOADING
  ========================================================= */

  if (loading) {
    return (
      <main className="resources-page">
        <div className="resources-container">
          <div className="resources-loading">
            <RefreshCw
              size={22}
              className="spin"
            />

            <span>
              Loading hospital resources...
            </span>
          </div>
        </div>
      </main>
    );
  }

  /* =========================================================
     RENDER
  ========================================================= */

  return (
    <main className="resources-page">
      <div className="resources-container">

        {/* =================================================
            HEADER
        ================================================= */}

        <section className="resources-header">

          <div>
            <div className="resources-eyebrow">
              <Activity size={15} />

              <span>
                RESOURCE MANAGEMENT
              </span>
            </div>

            <h1>
              Resource Command Center
            </h1>

            <p>
              Monitor beds, staff, and equipment
              across the hospital in real time.
            </p>
          </div>

          <button
            type="button"
            className="refresh-button"
            onClick={() =>
              loadResources(true)
            }
            disabled={refreshing}
          >
            <RefreshCw
              size={15}
              className={
                refreshing
                  ? "spin"
                  : ""
              }
            />

            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>

        </section>

        {/* =================================================
            ERROR
        ================================================= */}

        {error && (
          <div className="resources-error">
            <AlertCircle size={17} />

            <span>
              {error}
            </span>
          </div>
        )}

        {/* =================================================
            RESOURCE SUMMARY
        ================================================= */}

        <section className="resource-summary-grid">

          {/* BEDS */}

          <ResourceSummaryCard
            icon={<BedDouble size={20} />}
            title="Beds"
            total={bedStats.total}
            available={bedStats.available}
            secondaryLabel="Occupied"
            secondaryValue={bedStats.occupied}
          />

          {/* STAFF */}

          <ResourceSummaryCard
            icon={<Users size={20} />}
            title="Staff"
            total={staffStats.total}
            available={staffStats.available}
            secondaryLabel="Busy"
            secondaryValue={staffStats.busy}
          />

          {/* EQUIPMENT */}

          <ResourceSummaryCard
            icon={<Cpu size={20} />}
            title="Equipment"
            total={equipmentStats.total}
            available={equipmentStats.available}
            secondaryLabel="In Use"
            secondaryValue={equipmentStats.occupied}
          />

        </section>

        {/* =================================================
            BED INVENTORY
        ================================================= */}

        <ResourceTableCard
          icon={<BedDouble size={18} />}
          title="Bed Inventory"
          description="Current operational state of hospital beds."
          count={beds.length}
        >

          {beds.length === 0 ? (
            <EmptyTableState message="No bed records found." />
          ) : (
            <div className="resource-table-wrapper">

              <table className="resource-table">

                <thead>
                  <tr>
                    <th>BED ID</th>
                    <th>WARD</th>
                    <th>STATUS</th>
                    <th>PATIENT</th>
                    <th>EXPECTED RELEASE</th>
                  </tr>
                </thead>

                <tbody>
                  {beds.map((bed) => (
                    <tr key={bed.bed_id}>

                      <td>
                        <strong>
                          {bed.bed_id}
                        </strong>
                      </td>

                      <td>
                        {bed.ward || "—"}
                      </td>

                      <td>
                        <span
                          className={`resource-status ${statusClass(
                            bed.status
                          )}`}
                        >
                          {formatStatus(
                            bed.status
                          )}
                        </span>
                      </td>

                      <td>
                        {bed.patient_id || "—"}
                      </td>

                      <td>
                        {bed.expected_release_at ||
                          "—"}
                      </td>

                    </tr>
                  ))}
                </tbody>

              </table>

            </div>
          )}

        </ResourceTableCard>

        {/* =================================================
            STAFF
        ================================================= */}

        <ResourceTableCard
          icon={<Users size={18} />}
          title="Staff Availability"
          description="Current operational availability of hospital staff."
          count={staff.length}
        >

          {staff.length === 0 ? (
            <EmptyTableState message="No staff records found." />
          ) : (
            <div className="resource-table-wrapper">

              <table className="resource-table">

                <thead>
                  <tr>
                    <th>STAFF ID</th>
                    <th>NAME</th>
                    <th>ROLE</th>
                    <th>DEPARTMENT</th>
                    <th>STATUS</th>
                  </tr>
                </thead>

                <tbody>
                  {staff.map((member) => (
                    <tr
                      key={member.staff_id}
                    >

                      <td>
                        <strong>
                          {member.staff_id}
                        </strong>
                      </td>

                      <td>
                        {member.name || "—"}
                      </td>

                      <td>
                        {member.role || "—"}
                      </td>

                      <td>
                        {member.department ||
                          "—"}
                      </td>

                      <td>
                        <span
                          className={`resource-status ${statusClass(
                            member.status
                          )}`}
                        >
                          {formatStatus(
                            member.status
                          )}
                        </span>
                      </td>

                    </tr>
                  ))}
                </tbody>

              </table>

            </div>
          )}

        </ResourceTableCard>

        {/* =================================================
            EQUIPMENT
        ================================================= */}

        <ResourceTableCard
          icon={<Cpu size={18} />}
          title="Equipment Status"
          description="Current availability and operational state of equipment."
          count={equipment.length}
        >

          {equipment.length === 0 ? (
            <EmptyTableState message="No equipment records found." />
          ) : (
            <div className="resource-table-wrapper">

              <table className="resource-table">

                <thead>
                  <tr>
                    <th>EQUIPMENT ID</th>
                    <th>TYPE</th>
                    <th>LOCATION</th>
                    <th>STATUS</th>
                  </tr>
                </thead>

                <tbody>
                  {equipment.map((item) => (
                    <tr
                      key={item.equipment_id}
                    >

                      <td>
                        <strong>
                          {item.equipment_id}
                        </strong>
                      </td>

                      <td>
                        {item.equipment_type ||
                          "—"}
                      </td>

                      <td>
                        {item.location || "—"}
                      </td>

                      <td>
                        <span
                          className={`resource-status ${statusClass(
                            item.status
                          )}`}
                        >
                          {formatStatus(
                            item.status
                          )}
                        </span>
                      </td>

                    </tr>
                  ))}
                </tbody>

              </table>

            </div>
          )}

        </ResourceTableCard>

      </div>
    </main>
  );
}

/* =========================================================
   SUMMARY CARD
========================================================= */

function ResourceSummaryCard({
  icon,
  title,
  total,
  available,
  secondaryLabel,
  secondaryValue,
}) {
  return (
    <div className="resource-summary-card">

      <div className="resource-summary-top">

        <div className="resource-summary-icon">
          {icon}
        </div>

        <span>
          {title}
        </span>

      </div>

      <div className="resource-summary-total">
        {total}
      </div>

      <div className="resource-summary-bottom">

        <div>
          <small>Available</small>

          <strong>
            {available}
          </strong>
        </div>

        <div>
          <small>
            {secondaryLabel}
          </small>

          <strong>
            {secondaryValue}
          </strong>
        </div>

      </div>

    </div>
  );
}

/* =========================================================
   TABLE CARD
========================================================= */

function ResourceTableCard({
  icon,
  title,
  description,
  count,
  children,
}) {
  return (
    <section className="resource-table-card">

      <div className="resource-table-header">

        <div className="resource-table-title">

          <div className="resource-table-icon">
            {icon}
          </div>

          <div>
            <h2>
              {title}
            </h2>

            <p>
              {description}
            </p>
          </div>

        </div>

        <span className="resource-count">
          {count}
        </span>

      </div>

      {children}

    </section>
  );
}

/* =========================================================
   EMPTY STATE
========================================================= */

function EmptyTableState({ message }) {
  return (
    <div className="resource-empty">
      <CheckCircle2 size={22} />

      <span>
        {message}
      </span>
    </div>
  );
}

export default Resources;
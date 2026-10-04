import { useEffect, useState } from "react";
import api from "../services/api";
import "./Notifications.css";

function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [acknowledgingId, setAcknowledgingId] = useState(null);
  const [error, setError] = useState("");

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get("/notifications");

      setNotifications(response.data.notifications || []);
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
      setError("Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleAcknowledge = async (notificationId) => {
    try {
      setAcknowledgingId(notificationId);

      await api.put(
        `/notifications/${notificationId}/acknowledge`
      );

      await fetchNotifications();
    } catch (err) {
      console.error("Failed to acknowledge notification:", err);

      const message =
        err.response?.data?.detail ||
        "Failed to acknowledge notification.";

      setError(message);
    } finally {
      setAcknowledgingId(null);
    }
  };

  const unreadCount = notifications.filter(
    (notification) => notification.status === "UNREAD"
  ).length;

  return (
    <div className="notifications-page">
      <div className="notifications-header">
        <div>
          <h1>Notifications</h1>
          <p>
            Operational alerts and resource coordination updates
          </p>
        </div>

        <div className="notification-summary">
          <span className="notification-count">
            {unreadCount}
          </span>
          <span>Unread</span>
        </div>
      </div>

      {error && (
        <div className="notification-error">
          {error}
        </div>
      )}

      {loading ? (
        <div className="notification-loading">
          Loading notifications...
        </div>
      ) : notifications.length === 0 ? (
        <div className="notification-empty">
          <h3>No notifications</h3>
          <p>
            There are currently no operational notifications.
          </p>
        </div>
      ) : (
        <div className="notifications-list">
          {notifications.map((notification) => (
            <div
              key={notification.notification_id}
              className={`notification-card ${
                notification.status === "ACKNOWLEDGED"
                  ? "acknowledged"
                  : "unread"
              }`}
            >
              <div className="notification-top">
                <div className="notification-title-section">
                  <span
                    className={`severity-badge ${notification.severity?.toLowerCase()}`}
                  >
                    {notification.severity}
                  </span>

                  <h3>{notification.title}</h3>
                </div>

                <span className="notification-status">
                  {notification.status}
                </span>
              </div>

              <p className="notification-message">
                {notification.message}
              </p>

              <div className="notification-meta">
                <span>
                  <strong>Department:</strong>{" "}
                  {notification.department || "N/A"}
                </span>

                <span>
                  <strong>Type:</strong>{" "}
                  {notification.notification_type}
                </span>

                <span>
                  <strong>Created:</strong>{" "}
                  {notification.created_at
                    ? new Date(
                        notification.created_at
                      ).toLocaleString()
                    : "N/A"}
                </span>
              </div>

              {notification.status === "ACKNOWLEDGED" ? (
                <div className="acknowledged-info">
                  ✓ Acknowledged by{" "}
                  <strong>
                    {notification.acknowledged_by || "User"}
                  </strong>
                </div>
              ) : (
                <button
                  className="acknowledge-button"
                  onClick={() =>
                    handleAcknowledge(
                      notification.notification_id
                    )
                  }
                  disabled={
                    acknowledgingId ===
                    notification.notification_id
                  }
                >
                  {acknowledgingId ===
                  notification.notification_id
                    ? "Acknowledging..."
                    : "Acknowledge"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Notifications;
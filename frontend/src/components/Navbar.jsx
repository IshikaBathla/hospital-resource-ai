import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
  LayoutDashboard,
  Users,
  BedDouble,
  Lightbulb,
  FlaskConical,
  Bell,
  LogOut,
} from "lucide-react";
import api from "../services/api";

function Navbar() {
  const navigate = useNavigate();

  const [unreadCount, setUnreadCount] = useState(0);

  /* =========================================================
     LOAD CURRENT UNREAD NOTIFICATIONS
  ========================================================= */

  const fetchUnreadNotifications = async () => {
    try {
      const response = await api.get("/notifications");

      const notifications =
        response.data.notifications || [];

      const unread = notifications.filter(
        (notification) =>
          notification.status === "UNREAD"
      ).length;

      setUnreadCount(unread);
    } catch (error) {
      console.error(
        "Failed to fetch notification count:",
        error
      );
    }
  };

  /* =========================================================
     INITIAL NOTIFICATION COUNT
  ========================================================= */

  useEffect(() => {
    fetchUnreadNotifications();
  }, []);

  /* =========================================================
     REAL-TIME NOTIFICATION MONITORING
  ========================================================= */

  useEffect(() => {
    const socket = new WebSocket(
      "ws://127.0.0.1:8000/ws/notifications"
    );

    socket.onopen = () => {
      console.log(
        "Navbar live notification connection established."
      );
    };

    socket.onmessage = (event) => {
      try {
        const realtimeNotification =
          JSON.parse(event.data);

        if (
          realtimeNotification.notification_id
        ) {
          setUnreadCount(
            (currentCount) => currentCount + 1
          );
        }
      } catch (error) {
        console.error(
          "Invalid real-time notification received:",
          error
        );
      }
    };

    socket.onerror = (error) => {
      console.error(
        "Navbar WebSocket error:",
        error
      );
    };

    socket.onclose = () => {
      console.log(
        "Navbar live notification connection closed."
      );
    };

    return () => {
      socket.close();
    };
  }, []);

  /* =========================================================
     LOGOUT
  ========================================================= */

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    localStorage.removeItem("user");

    navigate("/login", { replace: true });
  };

  return (
    <aside className="sidebar">

      {/* SIDEBAR TOP */}
      <div className="sidebar-top">

        {/* BRAND */}
        <div className="brand">
          <div className="brand-icon">
            <Activity
              size={21}
              strokeWidth={2.2}
            />
          </div>

          <div>
            <h2>Hospital AI</h2>
            <span>
              RESOURCE COMMAND CENTER
            </span>
          </div>
        </div>

        {/* NAVIGATION TITLE */}
        <div className="sidebar-section-title">
          OPERATIONS
        </div>

        {/* NAVIGATION */}
        <nav className="sidebar-nav">

          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "active" : ""
              }`
            }
          >
            <LayoutDashboard
              size={18}
              strokeWidth={1.9}
            />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/patients"
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "active" : ""
              }`
            }
          >
            <Users
              size={18}
              strokeWidth={1.9}
            />
            <span>Patients</span>
          </NavLink>

          <NavLink
            to="/resources"
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "active" : ""
              }`
            }
          >
            <BedDouble
              size={18}
              strokeWidth={1.9}
            />
            <span>Resources</span>
          </NavLink>

          <NavLink
            to="/recommendations"
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "active" : ""
              }`
            }
          >
            <Lightbulb
              size={18}
              strokeWidth={1.9}
            />
            <span>Recommendations</span>
          </NavLink>

          <NavLink
            to="/what-if"
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "active" : ""
              }`
            }
          >
            <FlaskConical
              size={18}
              strokeWidth={1.9}
            />
            <span>What-If Simulation</span>
          </NavLink>

          {/* NOTIFICATIONS */}
          <NavLink
            to="/notifications"
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "active" : ""
              }`
            }
          >
            <Bell
              size={18}
              strokeWidth={1.9}
            />

            <span>Notifications</span>

            {/* LIVE UNREAD BADGE */}
            {unreadCount > 0 && (
              <span
                style={{
                  marginLeft: "auto",
                  minWidth: "20px",
                  height: "20px",
                  padding: "0 6px",
                  borderRadius: "999px",
                  background: "#ef4444",
                  color: "#ffffff",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "11px",
                  fontWeight: 800,
                  lineHeight: 1,
                  boxShadow:
                    "0 2px 8px rgba(239, 68, 68, 0.35)",
                }}
              >
                {unreadCount > 99
                  ? "99+"
                  : unreadCount}
              </span>
            )}
          </NavLink>

        </nav>
      </div>

      {/* SIDEBAR BOTTOM */}
      <div className="sidebar-bottom">

        <div className="user-profile">
          <div className="avatar">
            H
          </div>

          <div className="user-info">
            <strong>
              Hospital Admin
            </strong>

            <span>
              System Coordinator
            </span>
          </div>
        </div>

        <button
          type="button"
          className="logout-button"
          onClick={handleLogout}
        >
          <LogOut
            size={16}
            strokeWidth={1.9}
          />

          <span>Logout</span>
        </button>

      </div>

    </aside>
  );
}

export default Navbar;
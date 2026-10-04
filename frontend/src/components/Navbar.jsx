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

function Navbar() {
  const navigate = useNavigate();

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
            <Activity size={21} strokeWidth={2.2} />
          </div>

          <div>
            <h2>Hospital AI</h2>
            <span>RESOURCE COMMAND CENTER</span>
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
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <LayoutDashboard size={18} strokeWidth={1.9} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/patients"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <Users size={18} strokeWidth={1.9} />
            <span>Patients</span>
          </NavLink>

          <NavLink
            to="/resources"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <BedDouble size={18} strokeWidth={1.9} />
            <span>Resources</span>
          </NavLink>

          <NavLink
            to="/recommendations"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <Lightbulb size={18} strokeWidth={1.9} />
            <span>Recommendations</span>
          </NavLink>

          <NavLink
            to="/what-if"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <FlaskConical size={18} strokeWidth={1.9} />
            <span>What-If Simulation</span>
          </NavLink>

          {/* Notifications */}
          <NavLink
            to="/notifications"
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <Bell size={18} strokeWidth={1.9} />
            <span>Notifications</span>
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
            <strong>Hospital Admin</strong>
            <span>System Coordinator</span>
          </div>
        </div>

        <button
          type="button"
          className="logout-button"
          onClick={handleLogout}
        >
          <LogOut size={16} strokeWidth={1.9} />
          <span>Logout</span>
        </button>

      </div>

    </aside>
  );
}

export default Navbar;
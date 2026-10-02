import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Patients from "./pages/Patients";
import Recommendations from "./pages/Recommendations";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* Login */}
        <Route
          path="/login"
          element={<Login />}
        />

        {/* Protected Routes */}
        <Route element={<ProtectedRoute />}>

          {/* Dashboard */}
          <Route
            path="/dashboard"
            element={
              <>
                <Navbar />
                <Dashboard />
              </>
            }
          />

          {/* Patients */}
          <Route
            path="/patients"
            element={
              <>
                <Navbar />
                <Patients />
              </>
            }
          />

          {/* Resources */}
          <Route
            path="/resources"
            element={
              <>
                <Navbar />

                <div className="placeholder-page">
                  <h2>Resources</h2>
                  <p>
                    Resource management module coming next.
                  </p>
                </div>
              </>
            }
          />

          {/* Recommendations */}
          <Route
            path="/recommendations"
            element={
              <>
                <Navbar />
                <Recommendations />
              </>
            }
          />

          {/* What-If Simulation */}
          <Route
            path="/what-if"
            element={
              <>
                <Navbar />

                <div className="placeholder-page">
                  <h2>What-If Simulation</h2>
                  <p>
                    Simulation workspace coming next.
                  </p>
                </div>
              </>
            }
          />

        </Route>

        {/* Root */}
        <Route
          path="/"
          element={
            <Navigate
              to="/dashboard"
              replace
            />
          }
        />

        {/* Unknown route */}
        <Route
          path="*"
          element={
            <Navigate
              to="/dashboard"
              replace
            />
          }
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
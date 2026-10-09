
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyEmail from "./pages/VerifyEmail";
import Dashboard from "./pages/Dashboard";
import Patients from "./pages/Patients";
import Resources from "./pages/Resources";
import Recommendations from "./pages/Recommendations";
import WhatIf from "./pages/WhatIf";
import Notifications from "./pages/Notifications";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<><Navbar /><Dashboard /></>} />
          <Route path="/patients" element={<><Navbar /><Patients /></>} />
          <Route path="/resources" element={<><Navbar /><Resources /></>} />
          <Route path="/recommendations" element={<><Navbar /><Recommendations /></>} />
          <Route path="/what-if" element={<><Navbar /><WhatIf /></>} />
          <Route path="/notifications" element={<><Navbar /><Notifications /></>} />
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

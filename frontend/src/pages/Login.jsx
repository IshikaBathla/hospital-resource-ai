import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, LockKeyhole, Mail, ArrowRight } from "lucide-react";
import api from "../services/api";

function Login() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await api.post("/auth/login", formData);

      const { access_token, user } = response.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("user", JSON.stringify(user));

      navigate("/dashboard");
    } catch (error) {
      const message =
        error.response?.data?.detail ||
        "Unable to sign in. Please check your credentials.";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-background-glow glow-one"></div>
      <div className="login-background-glow glow-two"></div>

      <div className="login-container">
        <div className="login-brand">
          <div className="login-logo">
            <Activity size={28} />
          </div>

          <div>
            <h1>MedFlow AI</h1>
            <p>Hospital Resource Command Center</p>
          </div>
        </div>

        <div className="login-card">
          <div className="login-heading">
            <span className="eyebrow">SECURE ACCESS</span>
            <h2>Welcome back</h2>
            <p>
              Sign in to manage hospital resources and operational
              recommendations.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email address</label>

              <div className="input-wrapper">
                <Mail size={18} />
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="admin@hospital.com"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>

              <div className="input-wrapper">
                <LockKeyhole size={18} />
                <input
                  id="password"
                  name="password"
                  type="password"
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            {error && <div className="login-error">{error}</div>}

            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading ? (
                <span>Signing in...</span>
              ) : (
                <>
                  <span>Sign in to Command Center</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="security-note">
            <LockKeyhole size={15} />
            <span>Protected hospital operations environment</span>
          </div>
        </div>

        <p className="login-footer">
          AI Hospital Resource Coordination System
        </p>
      </div>
    </div>
  );
}

export default Login;
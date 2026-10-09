
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  UserRound,
  Mail,
  LockKeyhole,
  ArrowRight,
} from "lucide-react";
import api from "../services/api";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (event) => {
    setForm((old) => ({ ...old, [event.target.name]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (form.password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      await api.post("/auth/register", {
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      });

      navigate("/verify-email", {
        state: { email: form.email.trim().toLowerCase() },
      });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to create account. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-background-glow glow-one" />
      <div className="login-background-glow glow-two" />

      <div className="login-container">
        <div className="login-brand">
          <div className="login-logo"><Activity size={28} /></div>
          <div>
            <h1>MedFlow AI</h1>
            <p>Hospital Resource Command Center</p>
          </div>
        </div>

        <div className="login-card">
          <div className="login-heading">
            <span className="eyebrow">CREATE ACCOUNT</span>
            <h2>Get started</h2>
            <p>Create an account. New accounts start with viewer access.</p>
          </div>

          <form onSubmit={submit}>
            <div className="form-group">
              <label htmlFor="name">Full name</label>
              <div className="input-wrapper">
                <UserRound size={18} />
                <input id="name" name="name" value={form.name}
                  onChange={update} minLength={2} maxLength={100}
                  placeholder="Your full name" required />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <div className="input-wrapper">
                <Mail size={18} />
                <input id="email" name="email" type="email"
                  value={form.email} onChange={update}
                  placeholder="you@example.com" required />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <div className="input-wrapper">
                <LockKeyhole size={18} />
                <input id="password" name="password" type="password"
                  value={form.password} onChange={update}
                  minLength={8} maxLength={128}
                  placeholder="At least 8 characters" required />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm password</label>
              <div className="input-wrapper">
                <LockKeyhole size={18} />
                <input id="confirmPassword" name="confirmPassword"
                  type="password" value={form.confirmPassword}
                  onChange={update} placeholder="Re-enter password" required />
              </div>
            </div>

            {error && <div className="login-error">{error}</div>}

            <button className="login-button" type="submit" disabled={loading}>
              {loading ? "Creating account..." : <>Create account <ArrowRight size={18} /></>}
            </button>
          </form>

          <div className="auth-switch">
            Already registered? <Link to="/login">Sign in</Link>
          </div>

          <div className="security-note">
            <LockKeyhole size={15} />
            <span>Email verification required before sign-in</span>
          </div>
        </div>

        <p className="login-footer">AI Hospital Resource Coordination System</p>
      </div>
    </div>
  );
}

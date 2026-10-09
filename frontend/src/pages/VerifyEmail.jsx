
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Activity, Mail, ShieldCheck, ArrowRight } from "lucide-react";
import api from "../services/api";

export default function VerifyEmail() {
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState(location.state?.email || "");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const verify = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      await api.post("/auth/verify-email", {
        email: email.trim().toLowerCase(),
        otp,
      });

      setMessage("Email verified successfully. Redirecting to sign in...");
      setTimeout(() => navigate("/login", { state: { email } }), 900);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to verify email. Check the code and try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    setError("");
    setMessage("");
    setResending(true);

    try {
      const response = await api.post("/auth/resend-otp", {
        email: email.trim().toLowerCase(),
      });
      setMessage(response.data?.message || "Check your email for a new code.");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to resend code.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-background-glow glow-one" />
      <div className="login-background-glow glow-two" />

      <div className="login-container">
        <div className="login-brand">
          <div className="login-logo"><Activity size={28} /></div>
          <div><h1>MedFlow AI</h1><p>Hospital Resource Command Center</p></div>
        </div>

        <div className="login-card">
          <div className="login-heading">
            <span className="eyebrow">EMAIL VERIFICATION</span>
            <h2>Check your inbox</h2>
            <p>Enter the 6-digit code sent to your email. It expires in 5 minutes.</p>
          </div>

          <form onSubmit={verify}>
            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <div className="input-wrapper">
                <Mail size={18} />
                <input id="email" type="email" value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com" required />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="otp">6-digit verification code</label>
              <div className="input-wrapper">
                <ShieldCheck size={18} />
                <input id="otp" inputMode="numeric" autoComplete="one-time-code"
                  maxLength={6} pattern="[0-9]{6}" value={otp}
                  onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000" required />
              </div>
            </div>

            {error && <div className="login-error">{error}</div>}
            {message && <div className="auth-success">{message}</div>}

            <button className="login-button" type="submit" disabled={loading}>
              {loading ? "Verifying..." : <>Verify email <ArrowRight size={18} /></>}
            </button>
          </form>

          <button className="auth-secondary-button" type="button"
            onClick={resend} disabled={resending || !email.trim()}>
            {resending ? "Sending..." : "Resend verification code"}
          </button>

          <div className="auth-switch">
            <Link to="/register">Back to registration</Link> · <Link to="/login">Sign in</Link>
          </div>
        </div>

        <p className="login-footer">AI Hospital Resource Coordination System</p>
      </div>
    </div>
  );
}

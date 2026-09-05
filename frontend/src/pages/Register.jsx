import API_BASE_URL from "../config.js";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import "./Register.css";

function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (loading) {
      return;
    }

    setError("");

    if (
      !username.trim() ||
      !email.trim() ||
      !password ||
      !confirmPassword
    ) {
      setError("Please fill in all fields.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/register`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: username.trim(),
            email: email.trim(),
            password,
          }),
        }
      );

      const responseText = await response.text();

      let data = null;

      try {
        data = responseText
          ? JSON.parse(responseText)
          : null;
      } catch {
        throw new Error(
          "The CivicPay backend returned an invalid response."
        );
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            data?.message ||
            "Unable to create your account."
        );
      }

      navigate("/login", {
        replace: true,
        state: {
          registered: true,
          email: email.trim(),
        },
      });
    } catch (err) {
      console.error("CivicPay registration error:", err);

      if (err instanceof TypeError) {
        setError(
          "CivicPay could not connect to the backend. Please start the FastAPI server."
        );
      } else {
        setError(
          err?.message ||
            "Unable to create your account. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-page">

      <div className="register-background">
        <div className="register-glow register-glow-one"></div>
        <div className="register-glow register-glow-two"></div>
        <div className="register-grid"></div>
      </div>

      <main className="register-content">

        <div className="register-brand">

          <div className="register-brand-icon">
            🛡️
          </div>

          <div>
            <div className="register-brand-name">
              CIVIC<span>PAY</span>
            </div>

            <div className="register-brand-subtitle">
              SECURITY
            </div>
          </div>

        </div>

        <section className="register-card">

          <div className="register-security-status">
            <span className="register-status-dot"></span>
            SECURE REGISTRATION
          </div>

          <div className="register-header">

            <div className="register-icon-wrapper">
              <div className="register-icon">
                🛡️
              </div>
            </div>

            <h1>
              Create your <span>account</span>
            </h1>

            <p>
              Join CivicPay and protect yourself from
              suspicious payment requests.
            </p>

          </div>

          {error && (
            <div className="register-error">

              <span className="register-error-icon">
                ⚠️
              </span>

              <div>
                <strong>Registration failed</strong>
                <p>{error}</p>
              </div>

            </div>
          )}

          <form
            className="register-form"
            onSubmit={handleSubmit}
          >

            <div className="register-field">

              <label htmlFor="username">
                Username
              </label>

              <div className="register-input-wrapper">

                <span className="register-input-icon">
                  👤
                </span>

                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(event) =>
                    setUsername(event.target.value)
                  }
                  placeholder="Choose a username"
                  autoComplete="username"
                  disabled={loading}
                />

              </div>

              <span className="register-field-hint">
                3–30 characters
              </span>

            </div>

            <div className="register-field">

              <label htmlFor="register-email">
                Email address
              </label>

              <div className="register-input-wrapper">

                <span className="register-input-icon">
                  ✉
                </span>

                <input
                  id="register-email"
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  placeholder="Enter your email"
                  autoComplete="email"
                  disabled={loading}
                />

              </div>

            </div>

            <div className="register-field">

              <label htmlFor="register-password">
                Password
              </label>

              <div className="register-input-wrapper">

                <span className="register-input-icon">
                  🔑
                </span>

                <input
                  id="register-password"
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="Create a password"
                  autoComplete="new-password"
                  disabled={loading}
                />

              </div>

              <span className="register-field-hint">
                Minimum 8 characters
              </span>

            </div>

            <div className="register-field">

              <label htmlFor="confirm-password">
                Confirm password
              </label>

              <div className="register-input-wrapper">

                <span className="register-input-icon">
                  🔐
                </span>

                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(event.target.value)
                  }
                  placeholder="Confirm your password"
                  autoComplete="new-password"
                  disabled={loading}
                />

              </div>

            </div>

            <button
              type="submit"
              className="register-button"
              disabled={loading}
            >

              {loading ? (
                <>
                  <span className="register-spinner"></span>
                  Creating account...
                </>
              ) : (
                <>
                  <span>🛡️</span>
                  Create secure account
                  <span className="register-button-arrow">
                    →
                  </span>
                </>
              )}

            </button>

          </form>

          <div className="register-security-info">

            <div className="register-security-info-icon">
              🔒
            </div>

            <div>
              <strong>
                Your password is protected
              </strong>

              <p>
                CivicPay securely hashes your password
                before storing it.
              </p>
            </div>

          </div>

          <div className="register-login-link">

            <span>
              Already have an account?
            </span>

            <button
              type="button"
              onClick={() => navigate("/login")}
              disabled={loading}
            >
              Sign in
              <span>→</span>
            </button>

          </div>

        </section>

        <div className="register-footer">

          <span>
            🛡️ CivicPay AI
          </span>

          <span className="register-footer-separator">
            •
          </span>

          <span>
            Payment Protection System
          </span>

        </div>

      </main>

    </div>
  );
}

export default Register;
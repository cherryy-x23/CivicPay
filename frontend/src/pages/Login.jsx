import API_BASE_URL from "../config.js";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import "./Login.css";
import { saveAuth } from "../auth.js";

function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState(
    location.state?.email || ""
  );

  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const registrationSuccess =
    location.state?.registered === true;

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (loading) {
      return;
    }

    setError("");

    if (!email.trim() || !password) {
      setError(
        "Please enter your email and password."
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
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
            "Login failed. Please check your credentials."
        );
      }

      if (!data?.access_token || !data?.user) {
        throw new Error(
          "Login succeeded, but authentication information was not returned."
        );
      }

      saveAuth(
        data.access_token,
        data.user
      );

      navigate("/", {
        replace: true,
      });

    } catch (err) {
      console.error(
        "CivicPay login error:",
        err
      );

      if (err instanceof TypeError) {
        setError(
          "CivicPay could not connect to the backend. Please start the FastAPI server."
        );
      } else {
        setError(
          err?.message ||
            "Unable to sign in. Please try again."
        );
      }

    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">

      {/* =====================================================
          BACKGROUND
      ====================================================== */}

      <div className="login-background">

        <div className="login-glow login-glow-one"></div>

        <div className="login-glow login-glow-two"></div>

        <div className="login-grid"></div>

      </div>

      {/* =====================================================
          MAIN CONTENT
      ====================================================== */}

      <main className="login-content">

        {/* ===================================================
            BRAND
        ==================================================== */}

        <div className="login-brand">

          <div className="login-brand-icon">
            🛡️
          </div>

          <div>

            <div className="login-brand-name">
              CIVIC<span>PAY</span>
            </div>

            <div className="login-brand-subtitle">
              SECURITY
            </div>

          </div>

        </div>

        {/* ===================================================
            LOGIN CARD
        ==================================================== */}

        <section className="login-card">

          {/* SECURE ACCESS */}

          <div className="login-security-status">

            <span className="security-status-dot"></span>

            SECURE ACCESS

          </div>

          {/* HEADER */}

          <div className="login-header">

            <div className="login-icon-wrapper">

              <div className="login-icon">
                🔐
              </div>

            </div>

            <h1>
              Welcome <span>back</span>
            </h1>

            <p>
              Sign in to securely analyze payment
              requests with CivicPay AI.
            </p>

          </div>

          {/* =================================================
              REGISTRATION SUCCESS
          ================================================== */}

          {registrationSuccess && (
            <div className="login-success">

              <span className="login-success-icon">
                ✓
              </span>

              <div>

                <strong>
                  Account created successfully
                </strong>

                <p>
                  Your CivicPay account is ready.
                  Please sign in to continue.
                </p>

              </div>

            </div>
          )}

          {/* =================================================
              ERROR
          ================================================== */}

          {error && (
            <div className="login-error">

              <span className="login-error-icon">
                ⚠️
              </span>

              <div>

                <strong>
                  Authentication failed
                </strong>

                <p>
                  {error}
                </p>

              </div>

            </div>
          )}

          {/* =================================================
              LOGIN FORM
          ================================================== */}

          <form
            className="login-form"
            onSubmit={handleSubmit}
          >

            {/* EMAIL */}

            <div className="login-field">

              <label htmlFor="email">
                Email address
              </label>

              <div className="login-input-wrapper">

                <span className="login-input-icon">
                  ✉
                </span>

                <input
                  id="email"
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

            {/* PASSWORD */}

            <div className="login-field">

              <div className="login-label-row">

                <label htmlFor="password">
                  Password
                </label>

                <span className="password-hint">
                  Protected
                </span>

              </div>

              <div className="login-input-wrapper">

                <span className="login-input-icon">
                  🔑
                </span>

                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  disabled={loading}
                />

              </div>

            </div>

            {/* LOGIN BUTTON */}

            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >

              {loading ? (
                <>
                  <span className="login-spinner"></span>
                  Authenticating...
                </>
              ) : (
                <>
                  <span>🔓</span>

                  Sign in securely

                  <span className="login-button-arrow">
                    →
                  </span>
                </>
              )}

            </button>

          </form>

          {/* =================================================
              SECURITY INFORMATION
          ================================================== */}

          <div className="login-security-info">

            <div className="security-info-icon">
              🛡️
            </div>

            <div>

              <strong>
                Your session is protected
              </strong>

              <p>
                CivicPay uses secure authentication
                before allowing payment analysis.
              </p>

            </div>

          </div>

          {/* =================================================
              CREATE ACCOUNT
          ================================================== */}

          <div className="login-register-link">

            <span>
              Don't have a CivicPay account?
            </span>

            <button
              type="button"
              onClick={() => navigate("/register")}
              disabled={loading}
            >
              Create an account
              <span>→</span>
            </button>

          </div>

        </section>

        {/* ===================================================
            FOOTER
        ==================================================== */}

        <div className="login-footer">

          <span>
            🛡️ CivicPay AI
          </span>

          <span className="login-footer-separator">
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

export default Login;
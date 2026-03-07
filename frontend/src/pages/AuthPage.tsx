import { useState } from "react";
import { FlowerIcon } from "../icons";

const API_URL = (import.meta as ImportMeta).env?.VITE_API_URL ?? "http://localhost:8000";

type AuthResult = {
  user_id: string;
  email: string;
  token: string;
};

type AuthPageProps = {
  onAuth: (result: AuthResult) => void;
};

type AuthTab = "login" | "register";
type ResetStep = "idle" | "request" | "confirm";

export default function AuthPage({ onAuth }: AuthPageProps) {
  const [tab, setTab] = useState<AuthTab>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Password reset state
  const [resetStep, setResetStep] = useState<ResetStep>("idle");
  const [resetEmail, setResetEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [copiedToken, setCopiedToken] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const clearMessages = () => {
    setError("");
    setSuccess("");
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = (await res.json()) as AuthResult & { detail?: string };
      if (!res.ok) throw new Error(data.detail || "Login failed");
      onAuth(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = (await res.json()) as AuthResult & { detail?: string };
      if (!res.ok) throw new Error(data.detail || "Registration failed");
      onAuth(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleResetRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/reset-request`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: resetEmail }),
      });
      const data = (await res.json()) as { reset_token?: string; detail?: string };
      if (!res.ok) throw new Error(data.detail || "Could not request reset");
      setCopiedToken(data.reset_token ?? "");
      setResetStep("confirm");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleResetConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    clearMessages();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/reset-confirm`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token: resetToken, new_password: newPassword }),
      });
      const data = (await res.json()) as { message?: string; detail?: string };
      if (!res.ok) throw new Error(data.detail || "Could not reset password");
      setSuccess("Password updated. You can now log in.");
      setResetStep("idle");
      setTab("login");
      setResetToken("");
      setNewPassword("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (resetStep !== "idle") {
    return (
      <div className="auth-shell">
        <div className="auth-card card">
          <div className="auth-logo">
            <FlowerIcon className="auth-logo-icon" />
            <span className="logo">synapse</span>
          </div>

          {resetStep === "request" && (
            <>
              <h2 className="auth-heading">reset password</h2>
              <p className="auth-sub">Enter your account email to get a reset token.</p>
              <form onSubmit={handleResetRequest} className="auth-form">
                <label className="auth-label">
                  email
                  <input
                    type="email"
                    className="auth-input"
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    required
                    autoFocus
                  />
                </label>
                {error && <p className="auth-error">{error}</p>}
                <button type="submit" className="auth-btn" disabled={busy}>
                  {busy ? "sending..." : "get reset token"}
                </button>
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => { setResetStep("idle"); clearMessages(); }}
                >
                  back to login
                </button>
              </form>
            </>
          )}

          {resetStep === "confirm" && (
            <>
              <h2 className="auth-heading">set new password</h2>
              {copiedToken && (
                <div className="auth-token-box">
                  <p className="auth-sub">Your reset token (copy it):</p>
                  <code className="auth-token">{copiedToken}</code>
                </div>
              )}
              <form onSubmit={handleResetConfirm} className="auth-form">
                <label className="auth-label">
                  reset token
                  <input
                    type="text"
                    className="auth-input"
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    placeholder="paste token here"
                    required
                  />
                </label>
                <label className="auth-label">
                  new password
                  <input
                    type="password"
                    className="auth-input"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    minLength={6}
                    required
                  />
                </label>
                {error && <p className="auth-error">{error}</p>}
                {success && <p className="auth-success">{success}</p>}
                <button type="submit" className="auth-btn" disabled={busy}>
                  {busy ? "updating..." : "set new password"}
                </button>
                <button
                  type="button"
                  className="auth-link"
                  onClick={() => { setResetStep("idle"); clearMessages(); }}
                >
                  back to login
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card card">
        <div className="auth-logo">
          <FlowerIcon className="auth-logo-icon" />
          <span className="logo">synapse</span>
        </div>

        <p className="auth-tagline">your personal reflection coach</p>

        <div className="tabs auth-tabs">
          <button
            type="button"
            className={tab === "login" ? "active" : ""}
            onClick={() => { setTab("login"); clearMessages(); }}
          >
            log in
          </button>
          <button
            type="button"
            className={tab === "register" ? "active" : ""}
            onClick={() => { setTab("register"); clearMessages(); }}
          >
            create account
          </button>
        </div>

        {tab === "login" && (
          <form onSubmit={handleLogin} className="auth-form">
            <label className="auth-label">
              email
              <input
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
              />
            </label>
            <label className="auth-label">
              password
              <input
                type="password"
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>
            {error && <p className="auth-error">{error}</p>}
            {success && <p className="auth-success">{success}</p>}
            <button type="submit" className="auth-btn" disabled={busy}>
              {busy ? "logging in..." : "log in"}
            </button>
            <button
              type="button"
              className="auth-link"
              onClick={() => { setResetStep("request"); setResetEmail(email); clearMessages(); }}
            >
              forgot password?
            </button>
          </form>
        )}

        {tab === "register" && (
          <form onSubmit={handleRegister} className="auth-form">
            <label className="auth-label">
              email
              <input
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="email"
              />
            </label>
            <label className="auth-label">
              password
              <input
                type="password"
                className="auth-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={6}
                required
                autoComplete="new-password"
              />
            </label>
            <p className="auth-hint">at least 6 characters</p>
            {error && <p className="auth-error">{error}</p>}
            <button type="submit" className="auth-btn" disabled={busy}>
              {busy ? "creating account..." : "create account"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

import Logo from "../components/Logo";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ErrorBanner } from "../components/Feedback";
import {
  acceptInvitation,
  forgotPassword,
  resendOtp,
  resendSignupOtp,
  resetPassword,
  startSignup,
  verifyInvitationOtp,
  verifyResetOtp,
  verifySignupOtp,
} from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

function PublicCard({ title, children }) {
  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="public-auth-title">
        <div className="login-brand"><Logo /></div>
        <h1 id="public-auth-title">{title}</h1>
        {children}
      </section>
    </main>
  );
}

function OtpFields({ value, onChange, disabled }) {
  return (
    <div className="field">
      <label htmlFor="otp-code">Verification code</label>
      <input
        id="otp-code"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]{6}"
        maxLength={6}
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
        required
        disabled={disabled}
      />
    </div>
  );
}

function ResendCodeButton({ challengeId, signup }) {
  const [resending, setResending] = useState(false);
  const [message, setMessage] = useState("");
  const resend = async () => {
    setResending(true);
    setMessage("");
    try {
      await (signup ? resendSignupOtp : resendOtp)({ challenge_id: challengeId });
      setMessage("A new verification code has been sent.");
    } catch (requestError) {
      setMessage(extractErrorMessage(requestError));
    } finally {
      setResending(false);
    }
  };
  return <div className="auth-links"><button className="btn btn-ghost" type="button" onClick={resend} disabled={resending}>{resending ? "Sending…" : "Resend code"}</button>{message && <div role="status">{message}</div>}</div>;
}

export function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "", business_name: "", mobile_number: "", username: "", password: "", confirm_password: "",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      const result = await startSignup(form);
      navigate(`/signup/verify?challenge=${encodeURIComponent(result.challenge_id)}`, { replace: true });
    } catch (requestError) {
      setError(extractErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <PublicCard title="Create your business account">
      <p>Verify your mobile number to create your workspace.</p>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field"><label htmlFor="full-name">Full name</label><input id="full-name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} autoComplete="name" required disabled={saving} /></div>
        <div className="field"><label htmlFor="business-name">Business name</label><input id="business-name" value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} autoComplete="organization" required disabled={saving} /></div>
        <div className="field"><label htmlFor="mobile-number">Mobile number</label><input id="mobile-number" value={form.mobile_number} onChange={(e) => setForm({ ...form, mobile_number: e.target.value })} autoComplete="tel" required disabled={saving} /></div>
        <div className="field"><label htmlFor="signup-username">Username</label><input id="signup-username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} autoComplete="username" required disabled={saving} /></div>
        <div className="field"><label htmlFor="signup-password">Password</label><input id="signup-password" type="password" minLength={12} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" required disabled={saving} /><div className="field-help">Use at least 12 characters.</div></div>
        <div className="field"><label htmlFor="signup-confirm-password">Confirm password</label><input id="signup-confirm-password" type="password" minLength={12} value={form.confirm_password} onChange={(e) => setForm({ ...form, confirm_password: e.target.value })} autoComplete="new-password" required disabled={saving} /></div>
        <button className="btn btn-primary login-submit" type="submit" disabled={saving}>{saving ? "Sending code…" : "Send verification code"}</button>
        <div className="auth-links"><Link to="/login">Back to sign in</Link></div>
      </form>
    </PublicCard>
  );
}

export function SignupVerification() {
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const challengeId = search.get("challenge");

  const submit = async (event) => {
    event.preventDefault();
    if (!challengeId) return setError("Start signup again to request a verification code.");
    setError(""); setSaving(true);
    try {
      await verifySignupOtp({ challenge_id: challengeId, code });
      await refresh();
      navigate("/", { replace: true });
    } catch (requestError) { setError(extractErrorMessage(requestError)); } finally { setSaving(false); }
  };
  return <PublicCard title="Verify your mobile number"><p>Enter the six-digit code sent to your mobile number.</p><form onSubmit={submit}><ErrorBanner message={error} /><OtpFields value={code} onChange={setCode} disabled={saving} /><button className="btn btn-primary login-submit" disabled={saving}>{saving ? "Verifying…" : "Verify and create workspace"}</button>{challengeId && <ResendCodeButton challengeId={challengeId} signup />}<div className="auth-links"><Link to="/signup">Start again</Link></div></form></PublicCard>;
}

export function ForgotPassword() {
  const [mobileNumber, setMobileNumber] = useState("");
  const [challengeId, setChallengeId] = useState(null);
  const [code, setCode] = useState("");
  const [grant, setGrant] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const begin = async (event) => {
    event.preventDefault(); setError(""); setSaving(true);
    try { const result = await forgotPassword({ mobile_number: mobileNumber }); setChallengeId(result.challenge_id); setMessage(result.message); }
    catch (requestError) { setError(extractErrorMessage(requestError)); } finally { setSaving(false); }
  };
  const verify = async (event) => {
    event.preventDefault(); setError(""); setSaving(true);
    try { const result = await verifyResetOtp({ challenge_id: challengeId, code }); setGrant(result.reset_grant); setMessage("Code verified. Choose a new password."); }
    catch (requestError) { setError(extractErrorMessage(requestError)); } finally { setSaving(false); }
  };
  const finish = async (event) => {
    event.preventDefault(); setError("");
    if (newPassword !== confirmPassword) return setError("Passwords do not match.");
    setSaving(true);
    try { await resetPassword({ reset_grant: grant, new_password: newPassword, confirm_password: confirmPassword }); navigate("/login", { replace: true, state: { resetComplete: true } }); }
    catch (requestError) { setError(extractErrorMessage(requestError)); } finally { setSaving(false); }
  };

  if (grant) return <PublicCard title="Choose a new password"><form onSubmit={finish}><ErrorBanner message={error} /><div className="field"><label htmlFor="reset-password">New password</label><input id="reset-password" type="password" minLength={12} autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required disabled={saving} /></div><div className="field"><label htmlFor="reset-confirm">Confirm password</label><input id="reset-confirm" type="password" minLength={12} autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required disabled={saving} /></div><button className="btn btn-primary login-submit" disabled={saving}>{saving ? "Resetting…" : "Reset password"}</button></form></PublicCard>;
  if (challengeId) return <PublicCard title="Verify your code"><p>{message}</p><form onSubmit={verify}><ErrorBanner message={error} /><OtpFields value={code} onChange={setCode} disabled={saving} /><button className="btn btn-primary login-submit" disabled={saving}>{saving ? "Verifying…" : "Verify code"}</button><ResendCodeButton challengeId={challengeId} /></form></PublicCard>;
  return <PublicCard title="Reset your password"><p>We will send a code if the mobile number is eligible for recovery.</p><form onSubmit={begin}><ErrorBanner message={error} /><div className="field"><label htmlFor="recovery-mobile">Mobile number</label><input id="recovery-mobile" autoComplete="tel" value={mobileNumber} onChange={(e) => setMobileNumber(e.target.value)} required disabled={saving} /></div><button className="btn btn-primary login-submit" disabled={saving}>{saving ? "Sending…" : "Send code"}</button><div className="auth-links"><Link to="/login">Back to sign in</Link></div></form></PublicCard>;
}

export function InvitationAcceptance() {
  const [search] = useSearchParams();
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", username: "", password: "", confirm_password: "" });
  const [challengeId, setChallengeId] = useState(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const token = search.get("token") || "";
  const begin = async (event) => {
    event.preventDefault(); setError("");
    if (!token) return setError("This invitation link is incomplete.");
    if (form.username && form.password !== form.confirm_password) return setError("Passwords do not match.");
    setSaving(true);
    try { const result = await acceptInvitation({ invitation_token: token, ...form }); setChallengeId(result.challenge_id); }
    catch (requestError) { setError(extractErrorMessage(requestError)); } finally { setSaving(false); }
  };
  const verify = async (event) => {
    event.preventDefault(); setError(""); setSaving(true);
    try { await verifyInvitationOtp({ challenge_id: challengeId, code }); await refresh(); navigate("/", { replace: true }); }
    catch (requestError) { setError(extractErrorMessage(requestError)); } finally { setSaving(false); }
  };
  if (challengeId) return <PublicCard title="Verify your invitation"><p>Enter the six-digit code sent to the invited mobile number.</p><form onSubmit={verify}><ErrorBanner message={error} /><OtpFields value={code} onChange={setCode} disabled={saving} /><button className="btn btn-primary login-submit" disabled={saving}>{saving ? "Verifying…" : "Join workspace"}</button><ResendCodeButton challengeId={challengeId} /></form></PublicCard>;
  return <PublicCard title="Join a workspace"><p>If you already have an account with this mobile number, enter only your current password and leave the other fields blank.</p><form onSubmit={begin}><ErrorBanner message={error} /><div className="field"><label htmlFor="invite-name">Full name</label><input id="invite-name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} autoComplete="name" disabled={saving} /></div><div className="field"><label htmlFor="invite-username">Username</label><input id="invite-username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} autoComplete="username" disabled={saving} /></div><div className="field"><label htmlFor="invite-password">Password</label><input id="invite-password" type="password" minLength={12} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" disabled={saving} /></div><div className="field"><label htmlFor="invite-confirm">Confirm password</label><input id="invite-confirm" type="password" minLength={12} value={form.confirm_password} onChange={(e) => setForm({ ...form, confirm_password: e.target.value })} autoComplete="new-password" disabled={saving} /></div><button className="btn btn-primary login-submit" disabled={saving}>{saving ? "Continuing…" : "Continue"}</button></form></PublicCard>;
}

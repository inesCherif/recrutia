import { useState } from "react";
import { authAPI, setToken } from "../api";

export default function LoginPage({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      let data;
      if (isRegister) {
        data = await authAPI.register(username, password, email || undefined);
      } else {
        data = await authAPI.login(username, password);
      }
      setToken(data.token);
      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="glass-card login-card">
        <h1>🤖 Recrutia</h1>
        <p>Plateforme de Recrutement IA — Multi-Agents</p>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Identifiant</label>
            <input
              className="input"
              type="text"
              placeholder="Votre identifiant"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          {isRegister && (
            <div className="form-group">
              <label>Email (optionnel)</label>
              <input
                className="input"
                type="email"
                placeholder="nom@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label>Mot de passe</label>
            <input
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button className="btn btn-primary btn-full btn-lg" type="submit" disabled={loading}>
            {loading ? <span className="spinner"></span> : isRegister ? "Créer un compte" : "Se connecter"}
          </button>
        </form>

        <div className="login-toggle">
          <button onClick={() => { setIsRegister(!isRegister); setError(""); }}>
            {isRegister ? "Déjà un compte ? Se connecter" : "Pas de compte ? S'inscrire"}
          </button>
        </div>
      </div>
    </div>
  );
}

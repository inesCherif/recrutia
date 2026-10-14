/**
 * API Client — Centralized fetch wrapper for all backend calls.
 * Includes global error handling with toast notification dispatch.
 */

const API_BASE = "http://localhost:8000/api";

// --- Toast Event System ---
// Components listen for "recrutia:toast" events on window.
export function dispatchToast(message, type = "error", duration = 5000) {
  window.dispatchEvent(
    new CustomEvent("recrutia:toast", {
      detail: { message, type, duration, id: Date.now() },
    })
  );
}

// --- Token Management ---

function getToken() {
  return localStorage.getItem("recrutia_token");
}

export function setToken(token) {
  localStorage.setItem("recrutia_token", token);
}

export function clearToken() {
  localStorage.removeItem("recrutia_token");
}

export function isAuthenticated() {
  return !!getToken();
}

// --- Core Request Wrapper ---

async function request(method, path, body = null) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, opts);
  } catch {
    // Network-level failure (offline, DNS, CORS, etc.)
    const msg = navigator.onLine
      ? "Le serveur ne répond pas. Vérifiez que le backend est lancé."
      : "Pas de connexion internet.";
    dispatchToast(msg, "error", 6000);
    throw new Error(msg);
  }

  let data;
  try {
    data = await res.json();
  } catch {
    dispatchToast("Réponse invalide du serveur.", "error");
    throw new Error("Invalid server response");
  }

  if (!res.ok) {
    const detail = data.detail || `Erreur ${res.status}`;
    // 401 = session expired → auto-logout
    if (res.status === 401) {
      clearToken();
      dispatchToast("Session expirée. Veuillez vous reconnecter.", "warning");
    } else {
      dispatchToast(detail, "error");
    }
    throw new Error(detail);
  }

  return data;
}

// --- Auth ---
export const authAPI = {
  register: (username, password, email) =>
    request("POST", "/auth/register", { username, password, email }),
  login: (username, password) =>
    request("POST", "/auth/login", { username, password }),
  me: () => request("GET", "/auth/me"),
};

// --- Chat ---
export const chatAPI = {
  send: (message) => request("POST", "/chat", { message }),
};

// --- Recruiter ---
export const recruiterAPI = {
  generateJob: (description) =>
    request("POST", "/recruiter/generate-job", { description }),
  scoreCandidates: (candidates, job_data) =>
    request("POST", "/recruiter/score-candidates", { candidates, job_data }),
  getOffers: () => request("GET", "/recruiter/offers"),
  saveOffer: (job_data, linkedin_post, offer_id, form_url) =>
    request("POST", "/recruiter/offers", { job_data, linkedin_post, offer_id, form_url }),
};

// --- Student ---
export const studentAPI = {
  analyzeCV: (cv_text) =>
    request("POST", "/student/analyze-cv", { cv_text }),
  searchJobs: (cv_text, cv_analysis, opts = {}) =>
    request("POST", "/student/search-jobs", {
      cv_text,
      cv_analysis,
      jobs_per_site: opts.jobs_per_site || 5,
      demo_mode: opts.demo_mode || false,
      location: opts.location || "",
      include_remote: opts.include_remote !== false,
      selected_sources: opts.selected_sources || null,
    }),
  generateApplication: (cv_text, job) =>
    request("POST", "/student/generate-application", { cv_text, job }),
};

// --- Upload ---
export async function uploadPDF(file) {
  const formData = new FormData();
  formData.append("file", file);

  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}/upload/pdf`, {
      method: "POST",
      headers,
      body: formData,
    });
  } catch {
    dispatchToast("Erreur réseau lors de l'upload.", "error");
    throw new Error("Upload network error");
  }

  let data;
  try {
    data = await res.json();
  } catch {
    dispatchToast("Réponse invalide lors de l'upload.", "error");
    throw new Error("Invalid upload response");
  }

  if (!res.ok) {
    const detail = data.detail || "Erreur upload";
    dispatchToast(detail, "error");
    throw new Error(detail);
  }
  return data;
}

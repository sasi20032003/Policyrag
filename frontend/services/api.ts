import axios from "axios";
import type {
  AuthResponse,
  ChatQueryResponse,
  CompareResponse,
  GraphResponse,
  Policy,
  User,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE_URL, timeout: 60000 });

// Automatically attach JWT token from localStorage to outgoing requests
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ── Auth Endpoints ────────────────────────────────────────────────────────────

export async function signupUser(email: string, password: string, fullName?: string): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/api/auth/signup", {
    email,
    password,
    full_name: fullName,
  });
  if (typeof window !== "undefined") {
    localStorage.setItem("auth_token", res.data.access_token);
    localStorage.setItem("user", JSON.stringify(res.data.user));
  }
  return res.data;
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/api/auth/login", { email, password });
  if (typeof window !== "undefined") {
    localStorage.setItem("auth_token", res.data.access_token);
    localStorage.setItem("user", JSON.stringify(res.data.user));
  }
  return res.data;
}

export async function getCurrentUser(): Promise<User> {
  const res = await api.get<User>("/api/auth/me");
  return res.data;
}

export function logoutUser(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user");
  }
}

export async function uploadPolicy(form: FormData) {
  const res = await api.post("/api/policies/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function listPolicies(): Promise<Policy[]> {
  const res = await api.get("/api/policies");
  return res.data;
}

export async function getPolicy(id: string): Promise<Policy> {
  const res = await api.get(`/api/policies/${id}`);
  return res.data;
}

export async function askQuestion(payload: {
  question: string;
  policy_id?: string;
  as_of_date?: string;
  top_k?: number;
}): Promise<ChatQueryResponse> {
  const res = await api.post("/api/chat/query", payload);
  return res.data;
}

export async function streamQuestion(
  payload: {
    question: string;
    policy_id?: string;
    as_of_date?: string;
    top_k?: number;
  },
  onEvent: (event: string, data: any) => void,
  onError?: (err: Error) => void
): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/chat/query/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Stream request failed with status ${res.status}`);
    }

    if (!res.body) {
      throw new Error("No response body received for streaming");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/^event:\s*(\w+)/m);
        const dataMatch = block.match(/^data:\s*(.+)$/m);
        const eventName = eventMatch ? eventMatch[1] : "message";
        if (dataMatch) {
          try {
            const parsedData = JSON.parse(dataMatch[1]);
            onEvent(eventName, parsedData);
          } catch {
            onEvent(eventName, dataMatch[1]);
          }
        }
      }
    }
  } catch (err: any) {
    if (onError) onError(err);
    else throw err;
  }
}


export async function comparePolicyVersions(
  policy_version_id_a: string,
  policy_version_id_b: string
): Promise<CompareResponse> {
  const res = await api.post("/api/policies/compare", {
    policy_version_id_a,
    policy_version_id_b,
  });
  return res.data;
}

export async function getPolicyGraph(policyId: string): Promise<GraphResponse> {
  const res = await api.get(`/api/graph/${policyId}`);
  return res.data;
}

export async function reprocessPolicy(policyId: string) {
  const res = await api.post(`/api/policies/${policyId}/reprocess`);
  return res.data;
}

export async function deletePolicy(policyId: string) {
  const res = await api.delete(`/api/policies/${policyId}`);
  return res.data;
}

export async function getHealth() {
  const res = await api.get("/api/health");
  return res.data;
}

export async function listOkfConcepts() {
  const res = await api.get("/api/okf/concepts");
  return res.data;
}

export async function getOkfConcept(conceptId: string) {
  const res = await api.get(`/api/okf/concepts/${conceptId}`);
  return res.data;
}

export async function getOkfGraph() {
  const res = await api.get("/api/okf/graph");
  return res.data;
}

export async function listPatients() {
  const res = await api.get("/api/patients/");
  return res.data;
}

export async function createPatient(data: any) {
  const res = await api.post("/api/patients/", data);
  return res.data;
}

export async function deletePatient(id: string) {
  const res = await api.delete(`/api/patients/${id}`);
  return res.data;
}

export async function chatPatient(payload: {
  question: string;
  patient_profile_id?: string;
  inline_profile?: any;
  policy_id?: string;
  top_k?: number;
}) {
  const res = await api.post("/api/patients/chat", payload);
  return res.data;
}


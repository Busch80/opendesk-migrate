import axios, { AxiosInstance } from "axios";

const baseURL = import.meta.env.VITE_API_URL || "";

export const api: AxiosInstance = axios.create({
  baseURL: `${baseURL}/api/v1`,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    // surface error to caller — leave specific UX to components
    return Promise.reject(err);
  },
);

export type Tenant = {
  id: string;
  code: string;
  display_name: string;
  opendesk_base_url: string | null;
  m365_tenant_id: string | null;
  status: "active" | "paused" | "archived";
  created_at: string;
  updated_at: string;
};

export type User = {
  id: string;
  tenant_id: string;
  m365_upn: string;
  display_name: string | null;
  mailbox_size_bytes: number | null;
  onedrive_used_bytes: number | null;
  status: "pending" | "active" | "migrated" | "error" | "needs_reauth";
  last_synced_at: string | null;
};

export type Job = {
  id: string;
  tenant_id: string;
  user_id: string;
  job_type: "mail" | "calendar" | "contacts" | "onedrive";
  phase: "discovery" | "full" | "delta" | "verify" | "complete" | "failed" | "cancelled";
  total_items: number;
  processed: number;
  errors: number;
  last_error: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type Health = {
  status: string;
  version: string;
  database: string;
  storage?: Record<string, unknown>;
};

import { useQuery } from "@tanstack/react-query";
import type { Health, Job, Tenant } from "./api.ts";
import { api } from "./api.ts";

export const useHealth = () =>
  useQuery<Health>({
    queryKey: ["health"],
    queryFn: async () => (await api.get<Health>("/health")).data,
    refetchInterval: 10_000,
  });

export const useTenants = () =>
  useQuery<Tenant[]>({
    queryKey: ["tenants"],
    queryFn: async () => (await api.get<Tenant[]>("/tenants")).data,
  });

export const useTenant = (id: string | undefined) =>
  useQuery<Tenant>({
    queryKey: ["tenant", id],
    queryFn: async () => (await api.get<Tenant>(`/tenants/${id}`)).data,
    enabled: !!id,
  });

export const useJobs = (tenantId?: string) =>
  useQuery<Job[]>({
    queryKey: ["jobs", tenantId],
    queryFn: async () => {
      const params = tenantId ? { tenant_id: tenantId } : undefined;
      const r = await api.get<Job[]>("/jobs", { params });
      return r.data;
    },
  });

export const useJob = (id: string | undefined) =>
  useQuery<Job>({
    queryKey: ["job", id],
    queryFn: async () => (await api.get<Job>(`/jobs/${id}`)).data,
    enabled: !!id,
    refetchInterval: 5_000,
  });

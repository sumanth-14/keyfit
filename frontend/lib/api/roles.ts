import { apiFetch } from "./client";

export interface RoleOption {
  id: string;
  display_name: string;
}

export async function listRoles(accessToken: string): Promise<RoleOption[]> {
  const data = await apiFetch<{ roles: RoleOption[] }>("/api/roles/available", {
    accessToken,
  });
  return data.roles;
}

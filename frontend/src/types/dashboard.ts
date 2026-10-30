import { Role } from "./auth";

export interface Dashboard {
  id: number;
  slug: string;
  title: string;
  description: string;
  category: string;
  superset_dashboard_id: string;
  is_active: boolean;
  requires_branch_scope: boolean;
  allowed_roles: Role[];
  created_at: string;
  updated_at: string;
}

export interface GuestTokenResponse {
  token: string;
  superset_dashboard_id: string;
  superset_domain: string;
  expires_in: number;
  dashboard_title: string;
  requires_branch_scope: boolean;
}

export interface SupersetStatus {
  configured: boolean;
  superset_url: string;
  connected: boolean;
  status_detail: string;
}

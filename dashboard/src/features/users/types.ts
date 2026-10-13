/**
 * TypeScript interfaces for the Users admin module.
 */

export interface UserItem {
  id: string;
  email: string | null;
  name: string | null;
  company: string | null;
  role: string;
  organization_id: string | null;
  is_active: boolean;
  email_verified: boolean;
  two_factor_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  items: UserItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateUserPayload {
  email: string;
  name?: string;
  password: string;
  role: string;
  permissions?: string[];
}

export interface PermissionItemType {
  key: string;
  label: string;
  description: string | null;
  parent: string | null;
}

export interface CatalogModule {
  key: string;
  label: string;
  available: boolean;
  permissions: PermissionItemType[];
}

export interface PermissionCatalogResponse {
  modules: CatalogModule[];
}

export interface UserPermissionEntry {
  key: string;
  /** "role_template" | "user_override" | "user_deny" */
  source: string;
  /** False when source is "user_deny": role permission revoked for this user. */
  granted: boolean;
  granted_by: string | null;
  created_at: string | null;
}

export interface UserPermsResponse {
  user_id: string;
  role: string;
  permissions: UserPermissionEntry[];
}

export interface UserPermissionsUpdateResponse {
  user_id: string;
  granted: number;
  revoked: number;
}

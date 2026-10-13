/**
 * API client for admin user management.
 */
import { createModuleClient } from '../../../services/api/moduleClient';
import type {
  UserListResponse,
  UserItem,
  CreateUserPayload,
  UserPermsResponse,
  UserPermissionsUpdateResponse,
  PermissionCatalogResponse,
} from '../types';

const client = createModuleClient('/api/v1');

export const usersAdminApi = {
  /** List all users for the current tenant. */
  listUsers: (): Promise<UserListResponse> =>
    client.request<UserListResponse>(`${client.BASE}/users`),

  /** Create a new user. */
  createUser: (data: CreateUserPayload): Promise<UserItem> =>
    client.request<UserItem>(`${client.BASE}/users`, client.jsonPost(data)),

  /** Get permissions for a specific user. */
  getPermissions: (userId: string): Promise<UserPermsResponse> =>
    client.request<UserPermsResponse>(`${client.BASE}/users/${userId}/permissions`),

  /** Replace all per-user permission overrides.
   *
   * @param permissions Additive grants (extra permissions beyond the role)
   * @param denies      Role-template permissions to revoke for this user
   */
  setPermissions: (
    userId: string,
    permissions: string[],
    denies: string[] = [],
  ): Promise<UserPermissionsUpdateResponse> =>
    client.request<UserPermissionsUpdateResponse>(
      `${client.BASE}/users/${userId}/permissions`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ permissions, denies }),
      },
    ),

  /** Get the full permission catalog grouped by module. */
  getPermissionCatalog: (): Promise<PermissionCatalogResponse> =>
    client.request<PermissionCatalogResponse>(`${client.BASE}/permissions/catalog`),

  /** Deactivate (soft-delete) a user. */
  deactivateUser: (userId: string): Promise<void> =>
    client.voidRequest(`${client.BASE}/users/${userId}`, { method: 'DELETE' }).then(() => undefined),
};

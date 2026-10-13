export interface NavItem {
  label: string;
  path: string;
  permission: string;
  /** Optional SVG path data (d attribute) to render as an icon. */
  iconPath?: string;
  /** Optional grouping header. Adjacent items sharing the same section
   *  get rendered under the same header. Items without `section` render
   *  flat. Keeps the existing calendar/outbound/newsletter/captacion
   *  modules backwards-compatible. */
  section?: string;
  /** If true, only users with role 'superadmin' can see this item. */
  superadminOnly?: boolean;
}

export interface ModuleNav {
  module: string;
  feature: string;
  label: string;
  icon: string;
  basePath: string;
  color: { active: string; inactive: string; navLink: string };
  items: NavItem[];
}

// WhatsApp icons preserved from the previous hardcoded sidebar block.
const WA_ICONS = {
  inbox: 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-2.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4',
  templates: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  campaigns: 'M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z',
  contacts: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  segments: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
  tags: 'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z',
  analytics: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  catalog: 'M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z',
  sla: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  surveys: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z',
  dashboard: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z',
};

export const moduleNavigation: ModuleNav[] = [
  {
    module: 'whatsapp', feature: 'whatsapp', label: 'WhatsApp', icon: '\u{1F4AC}', basePath: '/whatsapp',
    color: { active: 'bg-green-600/20 text-green-400 border border-green-500/30', inactive: 'bg-green-900/30 border border-green-500/30 text-green-400 hover:bg-green-900/50', navLink: 'bg-green-600/20 text-green-400' },
    items: [
      { section: 'Principal', label: 'Inbox',       path: '/whatsapp',           permission: 'whatsapp.inbox.view',     iconPath: WA_ICONS.inbox },
      { section: 'Principal', label: 'Plantillas',  path: '/whatsapp/templates', permission: 'whatsapp.templates.view', iconPath: WA_ICONS.templates },
      { section: 'Principal', label: 'Campa\u00f1as',   path: '/whatsapp/campaigns', permission: 'whatsapp.campaigns.view', iconPath: WA_ICONS.campaigns },
      { section: 'Principal', label: 'Contactos',   path: '/whatsapp/contacts',  permission: 'whatsapp.contacts.view',  iconPath: WA_ICONS.contacts },
      { section: 'Principal', label: 'Segmentos',   path: '/whatsapp/segments',  permission: 'whatsapp.contacts.view',  iconPath: WA_ICONS.segments },
      { section: 'Principal', label: 'Etiquetas',   path: '/whatsapp/tags',      permission: 'whatsapp.contacts.view',  iconPath: WA_ICONS.tags },
      { section: 'CRM',              label: 'Analytics',  path: '/whatsapp/analytics', permission: 'whatsapp.analytics.view', iconPath: WA_ICONS.analytics },
      { section: 'Comercio',         label: 'Cat\u00e1logo',  path: '/whatsapp/catalog',   permission: 'whatsapp.commerce.view',  iconPath: WA_ICONS.catalog },
      { section: 'Automatizaci\u00f3n',  label: 'SLA',        path: '/whatsapp/sla',       permission: 'whatsapp.automation.manage', iconPath: WA_ICONS.sla },
      { section: 'Automatizaci\u00f3n',  label: 'Encuestas',  path: '/whatsapp/surveys',   permission: 'whatsapp.automation.manage', iconPath: WA_ICONS.surveys },
      { section: 'Anal\u00edtica',       label: 'Dashboard',  path: '/whatsapp/dashboard', permission: 'whatsapp.analytics.view', iconPath: WA_ICONS.dashboard },
    ],
  },
];

/**
 * Resolve the first sidebar destination a user can access. Used after
 * login when the user lacks the `dashboard` permission and we need to
 * land them somewhere useful.
 */
export function firstAccessibleRoute(
  hasFeature: (key: string) => boolean,
  hasPermission: (key: string) => boolean,
): string | null {
  // Dashboard first if granted.
  if (hasPermission('dashboard')) return '/';
  // Then any module the user can see.
  for (const mod of moduleNavigation) {
    if (!hasFeature(mod.feature)) continue;
    if (!hasPermission(mod.module)) continue;
    const item = mod.items.find((it) => hasPermission(it.permission));
    if (item) return item.path;
  }
  // Users panel (admin-only fallback).
  if (hasPermission('users.view')) return '/users';
  return null;
}

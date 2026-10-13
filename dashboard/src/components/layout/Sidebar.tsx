import React, { useCallback, useMemo } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import type { User } from '../../types';
import { useDashboard } from '../../context/DashboardContext';
import { useTenant } from '../../context/TenantContext';
import { useAuthorization } from '../../context/AuthorizationContext';
import { AVAILABLE_MODULES } from '../../config/modulesConfig';
import { moduleNavigation } from '../../config/navigationConfig';
import type { ModuleNav, NavItem } from '../../config/navigationConfig';

interface SidebarProps {
  user: User;
  onLogout: () => void;
  onOpenPrivacy: () => void;
  onOpenContact: () => void;
  onOpenMarketplace: () => void;
  onStartTour?: () => void;
  whatsAppSegments?: { id: string; name: string; slug: string; icon?: string; contact_count: number }[];
  activeSegmentId?: string | null;
  onSegmentClick?: (id: string | null) => void;
}

const segmentIcons: Record<string, string> = {
  'inbox': '\u{1F4E5}',
  'check-circle': '\u2705',
  'clock': '\u{1F551}',
  'phone': '\u{1F4DE}',
  'star': '\u2B50',
  'x-circle': '\u274C',
  'message-circle': '\u{1F4AC}',
};

const makeNavLinkClass = (activeClass: string) =>
  ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
      isActive ? activeClass : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'
    }`;

/** Group a module's items by their `section` field, preserving order. */
function groupBySection(items: NavItem[]): { section: string | null; items: NavItem[] }[] {
  const groups: { section: string | null; items: NavItem[] }[] = [];
  for (const item of items) {
    const key = item.section ?? null;
    const last = groups[groups.length - 1];
    if (last && last.section === key) {
      last.items.push(item);
    } else {
      groups.push({ section: key, items: [item] });
    }
  }
  return groups;
}

const Sidebar: React.FC<SidebarProps> = ({ user, onLogout, onOpenPrivacy, onOpenContact, onOpenMarketplace, onStartTour, whatsAppSegments, activeSegmentId, onSegmentClick }) => {
  const { visibleModules } = useDashboard();
  const { hasFeature } = useTenant();
  const { hasPermission } = useAuthorization();
  const location = useLocation();
  const navigate = useNavigate();

  const isDashboardRoute = location.pathname === '/';
  const isWhatsAppRoute = location.pathname.startsWith('/whatsapp');

  // The module whose sub-nav is currently shown (if we're inside one).
  const activeModule = useMemo<ModuleNav | null>(() => {
    if (isDashboardRoute) return null;
    return moduleNavigation.find((m) => location.pathname.startsWith(m.basePath)) ?? null;
  }, [location.pathname, isDashboardRoute]);

  // Should the WhatsApp "Segmentos" dynamic list render? Only inside
  // WhatsApp AND only if the user can actually see contact segments.
  const showWhatsAppSegments =
    isWhatsAppRoute && hasPermission('whatsapp.contacts.view');

  // Visible top-level modules for the current user. Computed once so the
  // sidebar doesn't re-check on every render of a child item.
  const visibleModuleEntries = useMemo(
    () =>
      moduleNavigation.filter(
        (m) =>
          hasFeature(m.feature as keyof import('../../types').TenantFeatures) &&
          hasPermission(m.module),
      ),
    [hasFeature, hasPermission],
  );

  const scrollToModule = useCallback((id: string) => {
    const element = document.getElementById(`module-${id}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  const canSeeDashboard = hasPermission('dashboard');
  const canSeeMarketplace = hasPermission('marketplace.view');

  return (
    <aside id="sidebar" className="fixed left-0 top-0 h-full w-64 bg-gray-800 border-r border-gray-700 pt-3 px-6 pb-6 z-40 flex flex-col">
      {/* Header */}
      <div className="mb-2 flex-shrink-0 px-2">
        <img src="/Logo Sfera AI.png" alt="Sfera AI" className="w-full h-auto" width={208} height={52} />
      </div>

      {/* Navegación principal */}
      <nav className="space-y-1 mb-2 flex-shrink-0">
        {canSeeDashboard && (
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `w-full text-sm flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              }`
            }
          >
            <span>📊</span>
            <span>Dashboard</span>
          </NavLink>
        )}
        {visibleModuleEntries.map((m) => (
          <NavLink
            key={m.module}
            to={m.basePath}
            className={({ isActive }) =>
              `w-full text-sm flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                isActive ? m.color.active : m.color.inactive
              }`
            }
          >
            <span>{m.icon}</span>
            <span>{m.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Botones de acción — Privacidad/Contacto siempre, Tienda y Usuarios gateados */}
      <nav className="space-y-1 mb-2 flex-shrink-0">
        <button
          id="privacy-button"
          onClick={onOpenPrivacy}
          className="w-full text-left text-sm flex items-center gap-2 px-3 py-2 rounded-lg transition bg-green-900/30 border border-green-500/30 text-green-400 hover:bg-green-900/50"
        >
          🔒 Privacidad y Datos
        </button>
        {canSeeMarketplace && (
          <button
            id="marketplace-button"
            onClick={onOpenMarketplace}
            className="w-full text-left text-sm flex items-center gap-2 px-3 py-2 rounded-lg transition bg-purple-900/30 border border-purple-500/30 text-purple-400 hover:bg-purple-900/50"
          >
            🛍️ Tienda
          </button>
        )}
        {hasPermission('users.view') && (
          <NavLink
            to="/users"
            className={({ isActive }) =>
              `w-full text-sm flex items-center gap-2 px-3 py-2 rounded-lg transition ${
                isActive
                  ? 'bg-yellow-600/20 text-yellow-400 border border-yellow-500/30'
                  : 'bg-yellow-900/30 border border-yellow-500/30 text-yellow-400 hover:bg-yellow-900/50'
              }`
            }
          >
            <span>👥</span>
            <span>Usuarios</span>
          </NavLink>
        )}
      </nav>

      {/* Lista de módulos activos (solo en el dashboard y solo si se tiene acceso) */}
      {isDashboardRoute && canSeeDashboard && (
        <div className="flex-1 min-h-0 flex flex-col mb-4">
          <div className="text-xs text-gray-500 uppercase font-semibold mb-2 flex-shrink-0">
            Módulos Activos ({visibleModules.length})
          </div>
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {visibleModules.map((id) => {
              const module = AVAILABLE_MODULES.find((m) => m.id === id);
              return module ? (
                <button
                  key={id}
                  onClick={() => scrollToModule(id)}
                  className="w-full text-sm text-gray-400 flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-700 hover:text-white transition-colors cursor-pointer text-left"
                >
                  <span>{module.icon}</span>
                  <span className="truncate">{module.name}</span>
                </button>
              ) : null;
            })}
            {visibleModules.length === 0 && (
              <p className="text-sm text-gray-500 italic px-2">No hay módulos activos</p>
            )}
          </div>
        </div>
      )}

      {/* Sub-navegación del módulo activo — unificada, con permisos por ítem */}
      {activeModule && (
        <div className="flex-1 min-h-0 flex flex-col overflow-y-auto mb-2">
          {groupBySection(activeModule.items).map((group, groupIndex) => {
            const visibleItems = group.items.filter((it) =>
              hasPermission(it.permission) &&
              (!it.superadminOnly || user.role === 'superadmin')
            );
            if (visibleItems.length === 0) return null;
            return (
              <div
                key={`${activeModule.module}-${group.section ?? 'flat'}-${groupIndex}`}
                className={`px-1 py-2 ${groupIndex > 0 ? 'border-t border-gray-700/50' : ''}`}
              >
                <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                  {group.section ?? activeModule.label}
                </p>
                {visibleItems.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === activeModule.basePath}
                    className={makeNavLinkClass(activeModule.color.navLink)}
                  >
                    {item.iconPath && (
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={item.iconPath} />
                      </svg>
                    )}
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            );
          })}

          {/* Segmentos dinámicos de WhatsApp (contexto, no declarativos) */}
          {showWhatsAppSegments && whatsAppSegments && whatsAppSegments.length > 0 && (
            <div className="px-1 py-2 border-t border-gray-700/50">
              <p className="px-2 text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                Segmentos
              </p>
              <button
                onClick={() => { onSegmentClick?.(null); navigate('/whatsapp'); }}
                className={`w-full flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
                  !activeSegmentId ? 'bg-green-600/20 text-green-400' : 'text-gray-400 hover:bg-gray-700/50'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-gray-500" />
                <span>Todos</span>
                <span className="ml-auto text-[10px] text-gray-600">
                  {whatsAppSegments.reduce((sum, s) => sum + s.contact_count, 0)}
                </span>
              </button>
              {whatsAppSegments.filter((s) => s.slug !== 'todos').map((seg) => (
                <button
                  key={seg.id}
                  onClick={() => { onSegmentClick?.(seg.id); navigate('/whatsapp'); }}
                  className={`w-full flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-colors ${
                    activeSegmentId === seg.id
                      ? 'bg-green-600/20 text-green-400'
                      : 'text-gray-400 hover:bg-gray-700/50'
                  }`}
                >
                  <span className="text-xs">{segmentIcons[seg.icon || ''] || '\u{1F3F7}'}</span>
                  <span className="truncate">{seg.name}</span>
                  {seg.contact_count > 0 && (
                    <span className="ml-auto text-[10px] text-gray-600">{seg.contact_count}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Spacer cuando no estamos en dashboard ni en módulo con sub-nav */}
      {!isDashboardRoute && !activeModule && <div className="flex-1" />}

      {/* Sección inferior fija */}
      <div className="flex-shrink-0">
        <button
          id="contact-button"
          onClick={onOpenContact}
          className="w-full text-left text-sm flex items-center gap-2 px-3 py-2 rounded-lg transition bg-cyan-900/30 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-900/50 mb-2"
        >
          📬 Contacto
        </button>
        <div className="bg-gray-900 rounded-lg px-3 py-2 mb-2">
          <p className="text-sm font-semibold text-white">{user.name}, <span className="text-gray-400 font-normal">{user.role}</span></p>
          <p className="text-xs text-gray-400">{user.company}</p>
        </div>
        <div className="flex gap-2">
          {onStartTour && (
            <button
              onClick={onStartTour}
              className="flex-1 px-3 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition text-sm"
              title="Ver tutorial"
            >
              ❓ Ayuda
            </button>
          )}
          <button
            onClick={onLogout}
            className={`px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition text-sm ${onStartTour ? 'flex-1' : 'w-full'}`}
          >
            🚪 Salir
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

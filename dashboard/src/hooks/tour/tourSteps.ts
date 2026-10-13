/**
 * Tour step definitions organized by route/page.
 *
 * Each key maps to a route pattern. The tour system picks the steps
 * for the current page only — no cross-page navigation during tours.
 *
 * IDs must match elements rendered on that specific page.
 */
import type { DriveStep } from 'driver.js';

// === SIDEBAR (shared, shown only on dashboard root tour) ===
export const sidebarSteps: DriveStep[] = [
  {
    element: '#sidebar',
    popover: {
      title: 'Navegación',
      description: 'Desde aquí accedes a todos los módulos contratados: llamadas, WhatsApp, newsletter, calendario y más.',
      side: 'right',
      align: 'start',
    },
  },
  {
    element: '#settings-button',
    popover: {
      title: 'Configurar Módulos',
      description: 'Elige qué módulos quieres ver en tu dashboard principal.',
      side: 'right',
    },
  },
  {
    element: '#privacy-button',
    popover: {
      title: 'Privacidad y Datos',
      description: 'Gestiona tus consentimientos y ejerce tus derechos sobre tus datos personales.',
      side: 'right',
    },
  },
  {
    element: '#marketplace-button',
    popover: {
      title: 'Tienda de Módulos',
      description: 'Explora y solicita nuevas funcionalidades para tu asistente virtual.',
      side: 'right',
    },
  },
  {
    element: '#contact-button',
    popover: {
      title: 'Soporte',
      description: 'Contacta con el equipo de soporte directamente desde aquí.',
      side: 'right',
    },
  },
];

// === DASHBOARD PRINCIPAL (/) ===
export const dashboardSteps: DriveStep[] = [
  {
    element: '#module-metrics-overview',
    popover: {
      title: 'Métricas del Mes',
      description: 'Llamadas totales, duración promedio, minutos y tasa de éxito. Se compara automáticamente con el mes anterior.',
      side: 'bottom',
    },
  },
  {
    element: '#module-call-stats',
    popover: {
      title: 'Estadísticas por Período',
      description: 'Análisis detallado por día, semana, mes y año con gráficos de distribución mensual.',
      side: 'bottom',
    },
  },
  {
    element: '#module-recent-calls',
    popover: {
      title: 'Últimas Llamadas',
      description: 'Haz clic en cualquier llamada para ver su transcripción, grabación y detalles.',
      side: 'top',
    },
  },
  {
    element: '#module-heatmap',
    popover: {
      title: 'Mapa de Calor',
      description: 'Visualiza la actividad por horas y días para identificar los picos de demanda.',
      side: 'top',
    },
  },
];


// === WHATSAPP ===
export const whatsappInboxSteps: DriveStep[] = [
  {
    element: '#wa-inbox-conversations',
    popover: {
      title: 'Conversaciones',
      description: 'Lista de conversaciones activas. Los mensajes no leídos aparecen destacados.',
      side: 'right',
    },
  },
  {
    element: '#wa-inbox-chat',
    popover: {
      title: 'Chat',
      description: 'Envía mensajes, plantillas y notas internas. Los mensajes se actualizan en tiempo real.',
      side: 'left',
    },
  },
  {
    element: '#wa-inbox-contact',
    popover: {
      title: 'Información del Contacto',
      description: 'Datos del contacto, segmentos asignados y etiquetas.',
      side: 'left',
    },
  },
];

export const whatsappTemplatesSteps: DriveStep[] = [
  {
    element: '#wa-templates-sync',
    popover: {
      title: 'Sincronizar Plantillas',
      description: 'Importa tus plantillas desde Meta. Las pendientes de aprobación se actualizan automáticamente.',
      side: 'bottom',
    },
  },
  {
    element: '#wa-templates-grid',
    popover: {
      title: 'Plantillas',
      description: 'Cada plantilla muestra su estado (borrador, pendiente, aprobada, rechazada) y las variables disponibles.',
      side: 'top',
    },
  },
];

export const whatsappCampaignsSteps: DriveStep[] = [
  {
    element: '#wa-campaigns-new',
    popover: {
      title: 'Nueva Campaña',
      description: 'Crea una campaña WhatsApp: elige plantilla, audiencia y programa el envío.',
      side: 'bottom',
    },
  },
  {
    element: '#wa-campaigns-list',
    popover: {
      title: 'Campañas',
      description: 'Progreso en tiempo real: enviados, entregados, leídos y fallidos.',
      side: 'top',
    },
  },
];

export const whatsappDashboardSteps: DriveStep[] = [
  {
    element: '#wa-dashboard-kpis',
    popover: {
      title: 'Métricas WhatsApp',
      description: 'Conversaciones abiertas, sin asignar, cerradas, contactos y brechas SLA.',
      side: 'bottom',
    },
  },
  {
    element: '#wa-dashboard-response',
    popover: {
      title: 'Tiempo de Respuesta',
      description: 'Promedio de los últimos 7 días. Indica la velocidad de atención al cliente.',
      side: 'top',
    },
  },
];

// === ROUTE → STEPS MAPPING ===

interface TourRoute {
  steps: DriveStep[];
  /** Include sidebar steps before module steps (only for dashboard root) */
  includeSidebar?: boolean;
}

/**
 * Maps route patterns to their tour steps.
 * Order matters: first match wins. More specific routes go first.
 */
export const tourRoutes: [string, TourRoute][] = [
  // Dashboard root — includes sidebar intro
  ['/', { steps: dashboardSteps, includeSidebar: true }],


  // WhatsApp
  ['/whatsapp/inbox', { steps: whatsappInboxSteps }],
  ['/whatsapp/templates', { steps: whatsappTemplatesSteps }],
  ['/whatsapp/campaigns', { steps: whatsappCampaignsSteps }],
  ['/whatsapp/dashboard', { steps: whatsappDashboardSteps }],
  ['/whatsapp', { steps: whatsappInboxSteps }], // default whatsapp = inbox
];

/**
 * Find tour steps for the current route.
 */
export function getStepsForRoute(pathname: string): { steps: DriveStep[]; includeSidebar: boolean } {
  for (const [pattern, config] of tourRoutes) {
    if (pattern === '/') {
      if (pathname === '/') return { steps: config.steps, includeSidebar: !!config.includeSidebar };
    } else if (pathname === pattern || pathname.startsWith(pattern + '/')) {
      return { steps: config.steps, includeSidebar: !!config.includeSidebar };
    }
  }
  // Fallback: sidebar-only tour
  return { steps: [], includeSidebar: true };
}

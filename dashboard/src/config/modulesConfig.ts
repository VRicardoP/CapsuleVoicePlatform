import type { ModuleConfig } from '../types';
import MetricsOverviewModule from '../components/modules/MetricsOverviewModule';
import WeeklyEvolutionModule from '../components/modules/WeeklyEvolutionModule';
import StatusDistributionModule from '../components/modules/StatusDistributionModule';
import RecentCallsModule from '../components/modules/RecentCallsModule';
import PerformanceRadarModule from '../components/modules/PerformanceRadarModule';
import HeatmapModule from '../components/modules/HeatmapModule';
import ConversionTrendsModule from '../components/modules/ConversionTrendsModule';
import TopMetricsModule from '../components/modules/TopMetricsModule';
import CallStatsModule from '../components/modules/CallStatsModule';
// Módulos GDPR/RGPD
import GdprComplianceScoreModule from '../components/modules/GdprComplianceScoreModule';
import GdprPendingRequestsModule from '../components/modules/GdprPendingRequestsModule';
import GdprBreachAlertsModule from '../components/modules/GdprBreachAlertsModule';
import GdprTrendsModule from '../components/modules/GdprTrendsModule';
import GdprConsentStatusModule from '../components/modules/GdprConsentStatusModule';
import VoiceQuotaModule from '../components/modules/VoiceQuotaModule';

export const AVAILABLE_MODULES: ModuleConfig[] = [
  {
    id: 'metrics-overview',
    name: 'Métricas Principales',
    description: 'KPIs clave del negocio',
    icon: '📊',
    category: 'metrics',
    defaultVisible: true,
    component: MetricsOverviewModule,
    requiredPermission: 'dashboard.calls.view',
  },
  {
    id: 'weekly-evolution',
    name: 'Evolución Semanal',
    description: 'Gráfico de tendencias',
    icon: '📈',
    category: 'charts',
    defaultVisible: true,
    component: WeeklyEvolutionModule,
    requiredPermission: 'dashboard.calls.view',
  },
  {
    id: 'status-distribution',
    name: 'Distribución de Estados',
    description: 'Resultados de llamadas',
    icon: '🎯',
    category: 'charts',
    defaultVisible: true,
    component: StatusDistributionModule,
    requiredPermission: 'dashboard.calls.view',
  },
  {
    id: 'recent-calls',
    name: 'Últimas Llamadas',
    description: 'Historial reciente',
    icon: '📞',
    category: 'tables',
    defaultVisible: true,
    component: RecentCallsModule,
    requiredPermission: 'dashboard.calls.view',
  },
  {
    id: 'performance-metrics',
    name: 'Performance IA',
    description: 'Radar de rendimiento',
    icon: '🤖',
    category: 'analytics',
    defaultVisible: true,
    component: PerformanceRadarModule,
    requiredPermission: 'dashboard.analytics.view',
  },
  {
    id: 'heatmap',
    name: 'Mapa de Calor',
    description: 'Actividad por horas',
    icon: '🔥',
    category: 'analytics',
    defaultVisible: true,
    component: HeatmapModule,
    requiredPermission: 'dashboard.analytics.view',
  },
  {
    id: 'conversion-trends',
    name: 'Conversión',
    description: 'Tendencias de ventas',
    icon: '💰',
    category: 'advanced',
    defaultVisible: false,
    component: ConversionTrendsModule,
    requiredPermission: 'dashboard.analytics.view',
  },
  {
    id: 'top-metrics',
    name: 'Metricas Avanzadas',
    description: 'KPIs secundarios',
    icon: '⭐',
    category: 'advanced',
    defaultVisible: false,
    component: TopMetricsModule,
    requiredPermission: 'dashboard.analytics.view',
  },
  {
    id: 'call-stats',
    name: 'Estadisticas por Periodo',
    description: 'Llamadas por ano, mes, semana y dia',
    icon: '📅',
    category: 'analytics',
    defaultVisible: true,
    component: CallStatsModule,
    requiredPermission: 'dashboard.calls.view',
  },
  // ============================================================================
  // CUOTA DE VOZ
  // ============================================================================
  {
    id: 'voice-quota',
    name: 'Cuota de Voz',
    description: 'Minutos de voz inbound/outbound usados este mes',
    icon: '🎙️',
    category: 'metrics',
    defaultVisible: true,
    component: VoiceQuotaModule,
    requiredPermission: 'dashboard.calls.view',
  },
  // ============================================================================
  // MODULOS GDPR/RGPD
  // ============================================================================
  {
    id: 'gdpr-compliance-score',
    name: 'Cumplimiento RGPD',
    description: 'Score global de cumplimiento normativo',
    icon: '🛡️',
    category: 'gdpr',
    defaultVisible: true,
    component: GdprComplianceScoreModule,
    requiredPermission: 'dashboard.gdpr.view',
  },
  {
    id: 'gdpr-pending-requests',
    name: 'Solicitudes ARCO',
    description: 'Solicitudes de derechos pendientes',
    icon: '📋',
    category: 'gdpr',
    defaultVisible: true,
    component: GdprPendingRequestsModule,
    requiredPermission: 'dashboard.gdpr.view',
  },
  {
    id: 'gdpr-breach-alerts',
    name: 'Alertas de Brechas',
    description: 'Incidentes de seguridad activos',
    icon: '🚨',
    category: 'gdpr',
    defaultVisible: true,
    component: GdprBreachAlertsModule,
    requiredPermission: 'dashboard.gdpr.view',
  },
  {
    id: 'gdpr-trends',
    name: 'Tendencias RGPD',
    description: 'Evolución del cumplimiento',
    icon: '📈',
    category: 'gdpr',
    defaultVisible: false,
    component: GdprTrendsModule,
    requiredPermission: 'dashboard.gdpr.view',
  },
  {
    id: 'gdpr-consent-status',
    name: 'Estado Consentimientos',
    description: 'Gestión de consentimientos por propósito',
    icon: '✓',
    category: 'gdpr',
    defaultVisible: false,
    component: GdprConsentStatusModule,
    requiredPermission: 'dashboard.gdpr.view',
  },
];
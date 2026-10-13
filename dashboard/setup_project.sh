#!/bin/bash

# Crear la estructura de carpetas
mkdir -p src/{types,context,hooks,config,data,components/{auth,layout,ui,modals,modules}}

# Crear los archivos si no existen
touch \
  src/types/index.ts \
  src/context/DashboardContext.tsx \
  src/hooks/useDashboard.ts \
  src/config/modulesConfig.ts \
  src/data/mockData.ts \
  src/components/auth/LoginScreen.tsx \
  src/components/layout/Sidebar.tsx \
  src/components/layout/Dashboard.tsx \
  src/components/ui/MetricCard.tsx \
  src/components/ui/ModuleWrapper.tsx \
  src/components/modals/CallDetailModal.tsx \
  src/components/modals/ModuleSettingsPanel.tsx \
  src/components/modules/MetricsOverviewModule.tsx \
  src/components/modules/WeeklyEvolutionModule.tsx \
  src/components/modules/StatusDistributionModule.tsx \
  src/components/modules/RecentCallsModule.tsx \
  src/components/modules/PerformanceRadarModule.tsx \
  src/components/modules/HeatmapModule.tsx \
  src/components/modules/ConversionTrendsModule.tsx \
  src/components/modules/TopMetricsModule.tsx \
  src/App.tsx

echo "✅ Estructura creada (archivos existentes fueron respetados)."

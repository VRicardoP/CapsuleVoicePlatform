import { useEffect, useCallback, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { driver, type DriveStep } from 'driver.js';
import 'driver.js/dist/driver.css';
import { sidebarSteps, getStepsForRoute } from './tour/tourSteps';

const TOUR_KEY_PREFIX = 'capsule_tour_';

/** Normalize pathname to a storage key: /outbound/campaigns → outbound_campaigns */
function routeKey(pathname: string): string {
  if (pathname === '/') return 'dashboard';
  return pathname.replace(/^\//, '').replace(/\//g, '_');
}

function hasSeenTour(pathname: string): boolean {
  return localStorage.getItem(TOUR_KEY_PREFIX + routeKey(pathname)) === 'true';
}

function markTourSeen(pathname: string): void {
  localStorage.setItem(TOUR_KEY_PREFIX + routeKey(pathname), 'true');
}

export const useOnboarding = () => {
  const { pathname } = useLocation();
  const [tourActive, setTourActive] = useState(false);
  const hasAutoStarted = useRef<string | null>(null);
  const driverRef = useRef<ReturnType<typeof driver> | null>(null);

  // Cleanup driver instance on unmount / navigation
  useEffect(() => {
    return () => { driverRef.current?.destroy(); };
  }, []);

  const startTour = useCallback(() => {
    const { steps: pageSteps, includeSidebar } = getStepsForRoute(pathname);

    // Build final steps: sidebar (only on dashboard root) + page-specific
    const allSteps: DriveStep[] = [
      ...(includeSidebar ? sidebarSteps : []),
      ...pageSteps,
    ];

    // Filter to elements that exist in DOM
    const visibleSteps = allSteps.filter(step => {
      if (!step.element) return true;
      if (typeof step.element === 'string') {
        return document.querySelector(step.element) !== null;
      }
      return true;
    });

    if (visibleSteps.length === 0) return;

    // Add closing step
    visibleSteps.push({
      popover: {
        title: '¡Listo!',
        description: 'Puedes repetir este tour en cualquier momento desde el botón de Ayuda.',
      },
    });

    // Destroy any previous driver instance before creating a new one
    driverRef.current?.destroy();

    setTourActive(true);

    const driverObj = driver({
      showProgress: true,
      steps: visibleSteps,
      nextBtnText: 'Siguiente',
      prevBtnText: 'Anterior',
      doneBtnText: 'Finalizar',
      progressText: '{{current}} de {{total}}',
      allowClose: true,
      overlayColor: 'rgba(0, 0, 0, 0.75)',
      stagePadding: 8,
      stageRadius: 8,
      popoverClass: 'capsule-tour-popover',
      onDestroyStarted: () => {
        markTourSeen(pathname);
        setTourActive(false);
        driverObj.destroy();
      },
    });

    driverRef.current = driverObj;
    driverObj.drive();
  }, [pathname]);

  // Auto-start for first visit to each page
  useEffect(() => {
    if (tourActive) return;
    if (hasAutoStarted.current === pathname) return;
    if (hasSeenTour(pathname)) return;

    hasAutoStarted.current = pathname;

    const timer = setTimeout(() => {
      if (document.getElementById('sidebar')) {
        startTour();
      }
    }, 800);

    return () => clearTimeout(timer);
  }, [pathname, tourActive, startTour]);

  const resetOnboarding = useCallback(() => {
    // Clear all tour keys
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key?.startsWith(TOUR_KEY_PREFIX)) {
        localStorage.removeItem(key);
      }
    }
  }, []);

  return { startTour, resetOnboarding };
};

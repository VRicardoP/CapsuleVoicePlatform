/**
 * Hook that returns a CSS class name for a micro-fade transition
 * when the watched value changes.
 *
 * Usage:
 *   const fadeClass = useAnimatedValue(someNumber);
 *   <span className={fadeClass}>{someNumber}</span>
 *
 * On change: opacity drops to 0.6 for 150ms, then fades back to 1.
 * First render is instant (no fade).
 */
import { useEffect, useRef, useState } from 'react';

export function useAnimatedValue(value: unknown): string {
  const [fading, setFading] = useState(false);
  const prevRef = useRef(value);
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      prevRef.current = value;
      return;
    }

    if (prevRef.current !== value) {
      prevRef.current = value;
      setFading(true);
      const timer = setTimeout(() => setFading(false), 300);
      return () => clearTimeout(timer);
    }
  }, [value]);

  return fading
    ? 'transition-opacity duration-300 opacity-60'
    : 'transition-opacity duration-300 opacity-100';
}

import { useCallback } from "react";

interface WindowPosition {
  x: number;
  y: number;
}

const STORAGE_PREFIX = "auralis-window-pos-";

/**
 * Hook to persist and restore window positions via localStorage.
 * Each window label gets its own storage key.
 */
export function useWindowPosition(windowLabel: string) {
  const savePosition = useCallback(
    (x: number, y: number) => {
      try {
        localStorage.setItem(
          `${STORAGE_PREFIX}${windowLabel}`,
          JSON.stringify({ x, y }),
        );
      } catch {
        // localStorage may be full or unavailable
      }
    },
    [windowLabel],
  );

  const loadPosition = useCallback((): WindowPosition | null => {
    try {
      const saved = localStorage.getItem(`${STORAGE_PREFIX}${windowLabel}`);
      if (saved) {
        return JSON.parse(saved) as WindowPosition;
      }
    } catch {
      // ignore parse errors
    }
    return null;
  }, [windowLabel]);

  const clearPosition = useCallback(() => {
    try {
      localStorage.removeItem(`${STORAGE_PREFIX}${windowLabel}`);
    } catch {
      // ignore
    }
  }, [windowLabel]);

  return { savePosition, loadPosition, clearPosition };
}

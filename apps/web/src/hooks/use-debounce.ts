"use client";
// apps/web/src/hooks/use-debounce.ts
// Hook useDebounce générique — retarde la propagation d'une valeur
// Utilisé pour la barre de recherche recettes (éviter un appel API à chaque frappe)

import { useState, useEffect } from "react";

export function useDebounce<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delayMs);

    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debouncedValue;
}

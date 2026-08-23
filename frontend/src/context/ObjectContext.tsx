import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

const STORAGE_KEY = "abrechnung.selectedObject";

interface ObjectContextValue {
  /** Gewähltes Objekt als String-ID (z. B. "3") oder null. */
  propertyFilter: string | null;
  setPropertyFilter: (v: string | null) => void;
}

const ObjectContext = createContext<ObjectContextValue | null>(null);

/**
 * Geteilte, persistente Objekt-Auswahl über alle Seiten mit Objekt-Selector.
 * Wird in localStorage gespeichert, damit die Auswahl auch nach Reload bleibt.
 */
export function ObjectProvider({ children }: { children: ReactNode }) {
  const [propertyFilter, setPropertyFilter] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });

  useEffect(() => {
    try {
      if (propertyFilter) localStorage.setItem(STORAGE_KEY, propertyFilter);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      // localStorage nicht verfügbar → ignorieren
    }
  }, [propertyFilter]);

  return (
    <ObjectContext.Provider value={{ propertyFilter, setPropertyFilter }}>
      {children}
    </ObjectContext.Provider>
  );
}

export function useObject(): ObjectContextValue {
  const ctx = useContext(ObjectContext);
  if (!ctx) throw new Error("useObject muss innerhalb von ObjectProvider verwendet werden");
  return ctx;
}

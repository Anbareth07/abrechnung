import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

interface TestDataContextValue {
  /** true → Testobjekte und deren Daten werden ausgeblendet. */
  hideTest: boolean;
  setHideTest: (v: boolean) => void;
}

const TestDataContext = createContext<TestDataContextValue>({
  hideTest: true,
  setHideTest: () => {},
});

const STORAGE_KEY = "abrechnung.hideTest";

export function TestDataProvider({ children }: { children: ReactNode }) {
  const [hideTest, setHideTestState] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) !== "0";
    } catch {
      return true;
    }
  });

  const setHideTest = (v: boolean) => {
    setHideTestState(v);
    try {
      localStorage.setItem(STORAGE_KEY, v ? "1" : "0");
    } catch {
      // ignore
    }
  };

  return (
    <TestDataContext.Provider value={{ hideTest, setHideTest }}>
      {children}
    </TestDataContext.Provider>
  );
}

export function useTestData(): TestDataContextValue {
  return useContext(TestDataContext);
}

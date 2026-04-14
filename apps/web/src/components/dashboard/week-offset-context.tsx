"use client";
// apps/web/src/components/dashboard/week-offset-context.tsx
// Contexte partagé entre WeekNavigator et DashboardContent
// Permet de faire remonter weekOffset sans prop drilling

import { createContext, useContext, useState } from "react";

interface WeekOffsetContextValue {
  weekOffset: number;
  setWeekOffset: (offset: number) => void;
}

const WeekOffsetContext = createContext<WeekOffsetContextValue | null>(null);

export function WeekOffsetProvider({ children }: { children: React.ReactNode }) {
  const [weekOffset, setWeekOffset] = useState(0);

  return (
    <WeekOffsetContext.Provider value={{ weekOffset, setWeekOffset }}>
      {children}
    </WeekOffsetContext.Provider>
  );
}

export function useWeekOffset(): WeekOffsetContextValue {
  const ctx = useContext(WeekOffsetContext);
  if (!ctx) {
    throw new Error("useWeekOffset doit être utilisé dans un WeekOffsetProvider");
  }
  return ctx;
}

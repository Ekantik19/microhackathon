"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { Mode } from "./types";

const KEY = "insidematch.mode";
const listeners = new Set<() => void>();

function read(): Mode {
  try {
    return window.localStorage.getItem(KEY) === "tactical" ? "tactical" : "casual";
  } catch {
    return "casual";
  }
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  window.addEventListener("storage", callback);
  return () => {
    listeners.delete(callback);
    window.removeEventListener("storage", callback);
  };
}

/** The viewer mode (Casual | Tactical), persisted in localStorage and shared by every component. */
export function useStoredMode(): [Mode, (m: Mode) => void] {
  const mode = useSyncExternalStore(subscribe, read, () => "casual" as Mode);
  const setMode = useCallback((m: Mode) => {
    try {
      window.localStorage.setItem(KEY, m);
    } catch {
      // storage blocked (private mode): the toggle still works for this page view via the listeners below
    }
    listeners.forEach((l) => l());
  }, []);
  return [mode, setMode];
}

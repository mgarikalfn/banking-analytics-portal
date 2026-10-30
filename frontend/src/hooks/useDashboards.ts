"use client";

import { useEffect, useState, useCallback } from "react";
import { Dashboard } from "@/types/dashboard";
import { fetchApi } from "@/lib/api";

export function useDashboards() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboards = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchApi<Dashboard[]>("/api/v1/dashboards/");
      setDashboards(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to load dashboards");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboards();
  }, [loadDashboards]);

  return { dashboards, isLoading, error, refetch: loadDashboards };
}

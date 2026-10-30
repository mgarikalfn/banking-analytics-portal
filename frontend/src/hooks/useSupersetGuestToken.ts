"use client";

import { useState, useCallback } from "react";
import { GuestTokenResponse } from "@/types/dashboard";
import { fetchApi } from "@/lib/api";

export function useSupersetGuestToken() {
  const [tokenData, setTokenData] = useState<GuestTokenResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchToken = useCallback(async (dashboardId: number): Promise<GuestTokenResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchApi<GuestTokenResponse>(
        "/api/v1/superset/guest-token",
        {
          method: "POST",
          body: JSON.stringify({ dashboard_id: dashboardId }),
        }
      );
      setTokenData(response);
      return response;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to obtain guest token";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { tokenData, isLoading, error, fetchToken };
}

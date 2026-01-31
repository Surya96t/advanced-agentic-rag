"use client";

import { useEffect } from "react";
import { useUser } from "@clerk/nextjs";

/**
 * Syncs the current user to the backend database on mount.
 * This ensures the user exists in Supabase before any operations.
 */
export function UserSync() {
  const { isLoaded, isSignedIn, user } = useUser();

  useEffect(() => {
    async function syncUser() {
      if (!isLoaded || !isSignedIn || !user) return;

      try {
        const response = await fetch("/api/auth/sync", {
          method: "POST",
        });

        if (!response.ok) {
          console.error("Failed to sync user:", await response.text());
        } else {
          console.log("User synced successfully");
        }
      } catch (error) {
        console.error("Error syncing user:", error);
      }
    }

    syncUser();
  }, [isLoaded, isSignedIn, user]);

  return null; // This component doesn't render anything
}

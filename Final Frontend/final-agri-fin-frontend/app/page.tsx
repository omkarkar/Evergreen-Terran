"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomeRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Check simple auth flag in localStorage
    const isAuthed =
      typeof window !== "undefined" &&
      localStorage.getItem("evergreen_auth") === "true";

    if (isAuthed) {
      // already logged in → go to dashboard
      router.replace("/dashboard");
    } else {
      // not logged in → go to login page first
      router.replace("/login");
    }
  }, [router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-100">
      <p className="text-sm text-slate-500">Opening Evergreen Terran…</p>
    </main>
  );
}

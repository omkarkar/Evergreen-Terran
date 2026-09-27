"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const DEMO_USERNAME = "officer";
const DEMO_PASSWORD = "evergreen123";

export default function OfficerLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  // If already logged in, skip login page
  useEffect(() => {
    if (typeof window === "undefined") return;
    const authed = localStorage.getItem("evergreen_auth") === "true";
    if (authed) {
      router.replace("/dashboard");
    }
  }, [router]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // Very simple demo auth
    if (username === DEMO_USERNAME && password === DEMO_PASSWORD) {
      if (typeof window !== "undefined") {
        localStorage.setItem("evergreen_auth", "true");
      }
      router.push("/dashboard");
    } else {
      setError("Invalid username or password. Use officer / evergreen123.");
    }
  }

  return (
    <main
      className="min-h-screen flex items-center justify-center bg-cover bg-center"
      style={{
        backgroundImage: "url('/evergreen terran background image.avif')",
      }}
    >
      <div className="w-full max-w-md bg-white/95 backdrop-blur-md rounded-3xl shadow-xl p-8 border border-emerald-50">
        {/* Logo */}
        <div className="flex justify-center mb-4">
          <img
            src="/evergreen-logo.png"
            alt="Evergreen Terran"
            className="h-10 w-10 object-contain"
          />
        </div>

        <h1 className="text-2xl font-bold text-center mb-1 text-emerald-800">
          Evergreen Terran
        </h1>
        <p className="text-center text-gray-700 mb-6 text-sm">
          Bank Officer Login
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-900">
              Username
            </label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white/80 text-gray-900 focus:outline-none focus:ring focus:ring-emerald-200"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1 text-gray-900">
              Password
            </label>
            <input
              type="password"
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white/80 text-gray-900 focus:outline-none focus:ring focus:ring-emerald-200"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="text-xs text-red-600 mt-1 text-center">{error}</p>
          )}

          <button
            type="submit"
            className="w-full rounded-lg bg-emerald-600 text-white py-2 text-sm font-semibold hover:bg-emerald-700 mt-2"
          >
            Login
          </button>
        </form>

        <p className="mt-4 text-[11px] text-center text-gray-700">
          Demo credentials:{" "}
          <span className="font-semibold">officer / evergreen123</span>
        </p>
      </div>
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

interface ApiResponse {
  report_text: string;
  summary: Record<string, any>;
}

export default function ReportPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // 🔐 Auth check – if not logged in, go to login page
  useEffect(() => {
    if (typeof window === "undefined") return;
    const authed = localStorage.getItem("evergreen_auth") === "true";
    if (!authed) router.replace("/login");
  }, [router]);

  const farmerName = searchParams.get("farmerName") || "";
  const country = searchParams.get("country") || "India";
  const crop = searchParams.get("crop") || "";
  const year = searchParams.get("year") || "";
  const farmSizeHa = searchParams.get("farmSizeHa") || "";
  const loanAmount = searchParams.get("loanAmount") || "";
  const interestRate = searchParams.get("interestRate") || "";
  const tenureMonths = searchParams.get("tenureMonths") || "";
  const emi = searchParams.get("emi") || "";
  const totalPayable = searchParams.get("totalPayable") || "";

  const [mlResult, setMlResult] = useState<ApiResponse | null>(null);
  const [mlError, setMlError] = useState<string | null>(null);

  function handlePrint() {
    if (typeof window !== "undefined") {
      window.print();
    }
  }

  // 🔍 Fetch ML predictions
  useEffect(() => {
    async function fetchPredictions() {
      try {
        setMlError(null);
        if (!farmerName || !country || !crop || !year) return;

        const res = await fetch(`${BACKEND_URL}/api/agri-report`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            farmer_name: farmerName,
            country,
            crop,
            current_year: Number(year),
            farm_size_ha: Number(farmSizeHa || "0"),
            loan_amount_usd: Number(loanAmount || "0"),
            annual_interest_rate: Number(interestRate || "0"),
            tenure_months: Number(tenureMonths || "0"),
          }),
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || "Backend error");
        }

        setMlResult((await res.json()) as ApiResponse);
      } catch (err: any) {
        setMlError(err.message || "Could not load predictions");
      }
    }

    fetchPredictions();
  }, [
    farmerName,
    country,
    crop,
    year,
    farmSizeHa,
    loanAmount,
    interestRate,
    tenureMonths,
  ]);

  const summary = mlResult?.summary || {};

  return (
    <main
      className="min-h-screen p-4 print:p-0 text-black flex items-start justify-center"
      style={{
        backgroundImage: 'url("/evergreen terran background image.avif")',
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
      }}
    >
      <div className="max-w-3xl w-full bg-white/95 shadow print:shadow-none p-8 rounded-md print:rounded-none text-sm leading-relaxed relative">
        {/* 🔹 Watermark */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-5 print:opacity-10">
          <img
            src="/evergreen-logo.png"
            alt="Evergreen Terran watermark"
            className="w-72 h-72 object-contain"
          />
        </div>

        {/* Content above watermark */}
        <div className="relative z-10">
          {/* HEADER */}
          <div className="flex justify-between items-start mb-6">
            <div className="flex items-center gap-3">
              <img
                src="/evergreen-logo.png"
                alt="Evergreen Terran Logo"
                className="w-12 h-12 object-contain"
              />
              <div>
                <h1 className="text-xl font-bold text-emerald-800">
                  Evergreen Terran
                </h1>
                <p className="text-xs text-gray-700">
                  Farmer Loan Assessment Report
                </p>
              </div>
            </div>

            <div className="text-right text-xs text-gray-800">
              <p>
                Date:{" "}
                {new Date().toLocaleDateString("en-IN", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                })}
              </p>
              <p>
                Time:{" "}
                {new Date().toLocaleTimeString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>

          <hr className="mb-4" />

          {/* 1. Farmer & Crop Details */}
          <section className="mb-4">
            <h2 className="font-semibold mb-2">1. Farmer &amp; Crop Details</h2>
            <div className="grid grid-cols-2 gap-1">
              <p>
                <span className="font-medium">Farmer name:</span> {farmerName}
              </p>
              <p>
                <span className="font-medium">Country:</span> {country}
              </p>
              <p>
                <span className="font-medium">Crop:</span> {crop}
              </p>
              <p>
                <span className="font-medium">Year:</span> {year}
              </p>
              <p>
                <span className="font-medium">Farm size (ha):</span>{" "}
                {farmSizeHa}
              </p>
            </div>
          </section>

          {/* 2. Loan Details */}
          <section className="mb-4">
            <h2 className="font-semibold mb-2">2. Loan Details</h2>
            <div className="grid grid-cols-2 gap-1">
              <p>
                <span className="font-medium">Loan amount:</span> {loanAmount}
              </p>
              <p>
                <span className="font-medium">Interest rate:</span>{" "}
                {interestRate}%
              </p>
              <p>
                <span className="font-medium">Tenure:</span> {tenureMonths}{" "}
                months
              </p>
            </div>
          </section>

          {/* 3. Repayment Summary */}
          <section className="mb-4">
            <h2 className="font-semibold mb-2">3. Repayment Summary</h2>
            <div className="grid grid-cols-2 gap-1">
              <p>
                <span className="font-medium">Estimated EMI:</span> {emi}
              </p>
              <p>
                <span className="font-medium">Total payable:</span>{" "}
                {totalPayable}
              </p>
            </div>
            <p className="text-xs text-gray-600 mt-2">
              * EMI values are approximate and for discussion purposes only.
            </p>
          </section>

          {/* 4. Officer Remarks */}
          <section className="mb-6">
            <h2 className="font-semibold mb-2">4. Officer Remarks</h2>
            <div className="border rounded-md h-24" />
          </section>

          {/* 5. Model Summary */}
          {mlError && (
            <p className="text-xs text-red-600 mb-4">{mlError}</p>
          )}

          {mlResult && (
            <section className="mb-6">
              <h2 className="font-semibold mb-2">
                5. Evergreen Terran&apos;s Predicted Summary
              </h2>
              <p className="text-xs text-gray-700 mb-2">
                Generated using Evergreen Terran&apos;s yield &amp; price
                prediction model.
              </p>

              <div className="grid grid-cols-2 gap-1">
                <p>
                  <span className="font-medium">Yield (ton/ha):</span>{" "}
                  {summary.predicted_yield_ton_per_ha?.toFixed?.(2)}
                </p>
                <p>
                  <span className="font-medium">Total production:</span>{" "}
                  {summary.total_production_tons?.toFixed?.(2)}
                </p>
                <p>
                  <span className="font-medium">Price (USD/ton):</span>{" "}
                  {summary.predicted_price_usd_per_ton?.toFixed?.(2)}
                </p>
                <p>
                  <span className="font-medium">Revenue (USD):</span>{" "}
                  {summary.revenue_usd?.toFixed?.(2)}
                </p>
                <p>
                  <span className="font-medium">Total cost (USD):</span>{" "}
                  {summary.total_cost_usd?.toFixed?.(2)}
                </p>
                <p>
                  <span className="font-medium">Profit (USD):</span>{" "}
                  {summary.profit_usd?.toFixed?.(2)}
                </p>
                <p>
                  <span className="font-medium">Capacity ratio:</span>{" "}
                  {summary.capacity_ratio?.toFixed?.(2)}
                </p>
                <p className="col-span-2">
                  <span className="font-medium">Decision:</span>{" "}
                  {summary.decision_text}
                </p>
              </div>
            </section>
          )}

          {/* Acknowledgements */}
          <section className="grid grid-cols-2 gap-6 text-xs mb-6 mt-6">
            <div>
              <h3 className="font-semibold mb-1">Farmer Acknowledgement</h3>
              <p className="mb-4">
                I have discussed all loan and repayment details with the bank
                officer.
              </p>
              <p>Signature: ____________________</p>
              <p>Name: {farmerName}</p>
              <p>Date: ____________________</p>
            </div>

            <div>
              <h3 className="font-semibold mb-1">Bank Officer</h3>
              <p className="mb-4">
                This assessment is generated using Evergreen Terran&apos;s
                model.
              </p>
              <p>Signature: ____________________</p>
              <p>Name: ____________________</p>
              <p>Branch: ____________________</p>
            </div>
          </section>

          {/* Buttons */}
          <div className="flex justify-end gap-3 mt-4 print:hidden">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border text-sm"
            >
              Back
            </button>

            <button
              onClick={handlePrint}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700"
            >
              Print / Save PDF
            </button>
          </div>

          <p className="text-[10px] text-gray-700 mt-4 print:mt-2">
            localhost:3000/report
          </p>
        </div>
      </div>
    </main>
  );
}

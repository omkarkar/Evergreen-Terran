"use client";

import { useMemo, useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

function calculateEmi(
  principal: number,
  annualRate: number,
  months: number
): { emi: number; totalPayable: number } {
  if (!principal || !annualRate || !months) {
    return { emi: 0, totalPayable: 0 };
  }

  const r = annualRate / 12 / 100;
  const n = months;

  if (r === 0) {
    const emiSimple = principal / n;
    return { emi: emiSimple, totalPayable: principal };
  }

  const pow = Math.pow(1 + r, n);
  const emi = (principal * r * pow) / (pow - 1);
  const totalPayable = emi * n;

  return { emi, totalPayable };
}

export default function OfficerDashboardPage() {
  const router = useRouter();

  // 🔒 Simple auth guard
  useEffect(() => {
    if (typeof window === "undefined") return;
    const authed = localStorage.getItem("evergreen_auth") === "true";
    if (!authed) {
      router.replace("/login");
    }
  }, [router]);

  function handleLogout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("evergreen_auth");
    }
    router.push("/login");
  }

  // ✅ Country is now just a free-text input
  const [farmerName, setFarmerName] = useState("Ram");
  const [country, setCountry] = useState("India"); // editable now
  const [crop, setCrop] = useState("Rice");
  const [year, setYear] = useState(new Date().getFullYear());
  const [farmSizeHa, setFarmSizeHa] = useState(5);
  const [loanAmount, setLoanAmount] = useState(20000);
  const [interestRate, setInterestRate] = useState(12);
  const [tenureMonths, setTenureMonths] = useState(12);

  const { emi, totalPayable } = useMemo(
    () => calculateEmi(loanAmount, interestRate, tenureMonths),
    [loanAmount, interestRate, tenureMonths]
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    try {
      await fetch(`${BACKEND_URL}/api/agri-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          farmer_name: farmerName,
          country,
          crop,
          current_year: year,
          farm_size_ha: farmSizeHa,
          loan_amount_usd: loanAmount,
          annual_interest_rate: interestRate,
          tenure_months: tenureMonths,
        }),
      });
    } catch {
      // ignore backend errors for now
    }

    const params = new URLSearchParams({
      farmerName,
      country,
      crop,
      year: String(year),
      farmSizeHa: String(farmSizeHa),
      loanAmount: String(loanAmount),
      interestRate: String(interestRate),
      tenureMonths: String(tenureMonths),
      emi: emi.toFixed(2),
      totalPayable: totalPayable.toFixed(2),
    });

    router.push(`/report?${params.toString()}`);
  }

  function handleClear() {
    setFarmerName("");
    setCountry("");
    setCrop("");
    setFarmSizeHa(0);
    setLoanAmount(0);
    setInterestRate(0);
    setTenureMonths(0);
  }

  return (
    <main
      className="min-h-screen bg-cover bg-center bg-fixed"
      style={{
        backgroundImage:
          'url("/evergreen terran background image.avif")',
        backgroundRepeat: "no-repeat",
        backgroundSize: "cover",
      }}
    >
      {/* dark overlay so content is readable */}
      <div className="min-h-screen bg-black/40">
        {/* Top navbar */}
        <header className="flex items-center justify-between px-10 py-4 shadow-sm bg-emerald-200/90">
          <div className="flex items-center gap-3">
            <img
              src="/evergreen-logo.png"
              alt="Evergreen Terran"
              className="h-10 w-10 object-contain"
            />
            <div>
              <h1 className="text-lg font-bold text-emerald-900">
                Evergreen Terran
              </h1>
              <p className="text-xs text-emerald-900/80">
                Bank Officer Workspace
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-sm">
            <span className="text-emerald-900">Logged in as</span>
            <span className="text-emerald-900 font-semibold">
              Officer (demo)
            </span>
            <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs font-semibold">
              OF
            </div>
            <button
              onClick={handleLogout}
              className="ml-2 px-3 py-1 rounded-lg border border-emerald-900/40 text-xs text-emerald-900 hover:bg-emerald-100"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Main layout */}
        <div className="max-w-6xl mx-auto py-8 px-4 md:px-6">
          <div className="grid md:grid-cols-[2.1fr,1.1fr] gap-6">
            {/* Left: form card */}
            <section className="bg-white rounded-3xl shadow-md px-8 py-6">
              <h2 className="text-lg font-semibold mb-1 text-gray-900">
                New Farmer Loan Appraisal
              </h2>
              <p className="text-xs text-gray-800 mb-5">
                Officer fills this form in front of the farmer. EMI and totals
                are calculated automatically.
              </p>

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Farmer & Crop details */}
                <div>
                  <h3 className="text-sm font-semibold mb-3 text-gray-900">
                    Farmer &amp; Crop Details
                  </h3>
                  <div className="grid md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Farmer name
                      </label>
                      <input
                        className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                        value={farmerName}
                        onChange={(e) => setFarmerName(e.target.value)}
                        required
                      />
                    </div>

                    {/* ✅ Country is now a normal input you can type in */}
                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Country
                      </label>
                      <input
                        className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                        required
                        placeholder="e.g. India"
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-3 mt-3">
                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Crop
                      </label>
                      <input
                        className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                        value={crop}
                        onChange={(e) => setCrop(e.target.value)}
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Year
                      </label>
                      <input
                        type="number"
                        className="w-full border rounded-md px-3 py-2 text-sm bg-white text-gray-900"
                        value={year}
                        onChange={(e) => setYear(Number(e.target.value))}
                        required
                      />
                    </div>
                  </div>

                  <div className="mt-3 max-w-xs">
                    <label className="block text-xs font-medium mb-1 text-gray-900">
                      Farm size (hectares)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                      value={farmSizeHa}
                      onChange={(e) => setFarmSizeHa(Number(e.target.value))}
                    />
                  </div>
                </div>

                {/* Loan details */}
                <div>
                  <h3 className="text-sm font-semibold mb-3 text-gray-900">
                    Loan Details
                  </h3>
                  <div className="grid md:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Loan amount
                      </label>
                      <input
                        type="number"
                        className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                        value={loanAmount}
                        onChange={(e) =>
                          setLoanAmount(Number(e.target.value) || 0)
                        }
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Interest (% per year)
                      </label>
                      <input
                        type="number"
                        className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                        value={interestRate}
                        onChange={(e) =>
                          setInterestRate(Number(e.target.value) || 0)
                        }
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium mb-1 text-gray-900">
                        Loan tenure (months)
                      </label>
                      <input
                        type="number"
                        className="w-full border rounded-md px-3 py-2 text-sm bg-slate-50 text-gray-900"
                        value={tenureMonths}
                        onChange={(e) =>
                          setTenureMonths(Number(e.target.value) || 0)
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={handleClear}
                    className="px-4 py-2 rounded-lg border border-gray-400 text-sm text-gray-900 hover:bg-slate-50"
                  >
                    Clear
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700"
                  >
                    Save appraisal &amp; view report
                  </button>
                </div>
              </form>
            </section>

            {/* Right: summary card */}
            <section className="bg-white rounded-3xl shadow-md p-6 h-fit">
              <h3 className="text-sm font-semibold mb-1 text-gray-900">
                Loan Summary (live)
              </h3>
              <p className="text-xs text-gray-800 mb-4">
                Updates automatically as you fill the form.
              </p>

              <dl className="space-y-2 text-sm text-gray-900">
                <div className="flex justify-between">
                  <dt className="text-gray-800">Farmer</dt>
                  <dd className="font-medium">{farmerName || "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-800">Crop</dt>
                  <dd className="font-medium">{crop || "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-800">Farm size (ha)</dt>
                  <dd className="font-medium">
                    {farmSizeHa ? farmSizeHa : "—"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-800">Loan amount</dt>
                  <dd className="font-semibold">
                    {loanAmount
                      ? loanAmount.toLocaleString("en-IN", {
                          maximumFractionDigits: 0,
                        })
                      : "—"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-800">Interest (p.a.)</dt>
                  <dd className="font-medium">
                    {interestRate ? `${interestRate} %` : "—"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-800">Tenure</dt>
                  <dd className="font-medium">
                    {tenureMonths ? `${tenureMonths} months` : "—"}
                  </dd>
                </div>

                <hr className="my-3" />

                <div className="flex justify-between">
                  <dt className="text-gray-800">Estimated EMI / month</dt>
                  <dd className="font-bold text-emerald-600">
                    {emi ? emi.toFixed(2) : "—"}
                  </dd>
                </div>

                <div className="flex justify-between">
                  <dt className="text-gray-800">Total payable</dt>
                  <dd className="font-bold">
                    {totalPayable ? totalPayable.toFixed(2) : "—"}
                  </dd>
                </div>
              </dl>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}

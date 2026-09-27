# src/backend_api.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List  # ✅ for type hints

# ⬇️ IMPORT MORE FROM agri_core (countries)
from .agri_core import (
    generate_agri_finance_report,
    ALL_YIELD_COUNTRIES,
    ALL_COP_COUNTRIES,
)

app = FastAPI()

# Allow your Next.js frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
] 
 
app.add_middleware( 
    CORSMiddleware, 
    allow_origins=origins, 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"], 
) 
 
# --- Simple health check endpoints --- 
 
@app.get("/") 
def root(): 
    return {"message": "Agri-Finance Backend is running"} 
 
@app.get("/health") 
def health(): 
    return {"status": "ok"} 
 
 
# --- Request / Response models --- 
 
class AgriReportRequest(BaseModel): 
    farmer_name: str 
    country: str 
    crop: str 
    current_year: int 
    farm_size_ha: float 
    loan_amount_usd: float 
    annual_interest_rate: float 
    tenure_months: int 
 
 
class AgriReportResponse(BaseModel): 
    report_text: str 
    summary: dict 
 
 
# ✅ NEW: response model for countries 
class CountryListResponse(BaseModel): 
    countries: List[str] 
 
 
# --- Main report endpoint --- 
 
@app.post("/api/agri-report", response_model=AgriReportResponse) 
def create_agri_report(req: AgriReportRequest): 
    report_text, summary = generate_agri_finance_report( 
        farmer_name=req.farmer_name, 
        country=req.country, 
        crop=req.crop, 
        current_year=req.current_year, 
        farm_size_ha=req.farm_size_ha, 
        loan_amount_usd=req.loan_amount_usd, 
        annual_interest_rate=req.annual_interest_rate, 
        tenure_months=req.tenure_months, 
    ) 
 
    if summary is None: 
        raise HTTPException(status_code=400, detail=report_text) 
 
    return {"report_text": report_text, "summary": summary} 
 
 
# ✅ NEW: endpoint to get list of countries for the frontend 
 
@app.get("/api/countries", response_model=CountryListResponse) 
def get_countries(): 
    """ 
    Return the list of countries known to the backend 
    (from yield_panel and crop_cop_per_ha tables). 
    Frontend will use this to populate the country dropdown. 
    """ 
    # union of both sets, sorted 
    countries = sorted(set(ALL_YIELD_COUNTRIES) | set(ALL_COP_COUNTRIES)) 
    return CountryListResponse(countries=countries) 

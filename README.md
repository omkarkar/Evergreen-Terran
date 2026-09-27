# 🌾 Evergreen Terran

**Evergreen Terran** is a data-driven agricultural finance decision-support application developed to assist with farmer loan appraisal and financial risk assessment.

The system combines crop-yield prediction, crop-price forecasting, cost-of-production estimation, expected profitability, and loan repayment analysis in a single web application. It is designed as a decision-support tool for agricultural lending scenarios.

The application consists of:

- A **Next.js frontend** for the bank-officer interface and printable farmer report
- A **FastAPI backend** that exposes the agricultural finance analysis through REST API endpoints
- A **PostgreSQL database** containing agricultural, environmental, price, and cost-of-production data
- A **machine-learning pipeline** for crop-yield prediction
- Rule-based financial calculations for loan repayment capacity

---

## 1. Main Features

### Crop Yield Prediction
The system predicts crop yield in **tons per hectare** using a trained machine-learning pipeline.

The yield model uses agricultural and environmental variables including:

- Year
- Average temperature
- Relative humidity
- Precipitation
- Temperature anomaly
- Precipitation anomaly
- Nitrogen fertilizer use
- Phosphorus fertilizer use
- Potassium fertilizer use
- Soil pH
- Soil organic carbon
- Soil nitrogen
- Country
- Crop

### Crop Price Forecasting
Evergreen Terran generates a **five-year crop price forecast** using historical Asia-wide standardized crop prices.

The forecasting method calculates an average annual growth rate from recent historical observations and limits annual growth to a range of **-5% to +5%** to reduce unrealistic long-term price growth.

### Cost of Production Estimation
The application retrieves cost-of-production information from PostgreSQL and estimates:

- Fertilizer cost
- Pesticide cost
- Irrigation cost
- Seed cost
- Other production costs
- Total production cost per hectare
- Total production cost for the selected farm size

### Revenue and Profit Estimation
Expected production is calculated as:

```text
Expected Production = Predicted Yield × Farm Size
```

Estimated revenue is calculated as:

```text
Estimated Revenue = Expected Production × Predicted Crop Price
```

Expected profit is calculated as:

```text
Expected Profit = Estimated Revenue - Total Production Cost
```

### Loan Repayment Assessment
The backend calculates simple loan repayment for the financial assessment:

```text
Total Interest = Loan Amount × Annual Interest Rate × (Tenure Months / 12)

Total Repayment = Loan Amount + Total Interest
```

The repayment-capacity ratio is:

```text
Capacity Ratio = Expected Profit / Total Repayment
```

The current decision rules are:

| Capacity Ratio | Interpretation |
|---|---|
| `>= 1.30` | Farmer can repay comfortably |
| `>= 1.00 and < 1.30` | Farmer can likely repay, but with some risk |
| `< 1.00` | High risk: expected profit may not fully cover repayment |

The frontend also displays an approximate monthly **EMI** using the standard reducing-balance EMI formula for discussion purposes.

### Printable Farmer Loan Assessment Report
The frontend generates a report containing:

- Farmer and crop information
- Loan information
- Estimated EMI
- Total payable amount
- Predicted crop yield
- Expected production
- Predicted crop price
- Revenue
- Production cost
- Profit
- Repayment-capacity ratio
- Loan-risk decision
- Farmer acknowledgement
- Bank-officer signature area

The report can be printed or saved as a PDF using the browser's print functionality.

---

## 2. Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- Pandas
- NumPy
- Scikit-learn
- XGBoost
- LightGBM
- Joblib
- SQLAlchemy
- PostgreSQL
- Psycopg2
- Uvicorn

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- HTML/CSS
- Browser Local Storage

### Machine Learning

Candidate algorithms used during yield-model training include:

- Random Forest Regressor
- Gradient Boosting Regressor
- XGBoost Regressor
- LightGBM Regressor
- Support Vector Regression (RBF)

The models are evaluated using **5-fold cross-validation**, and the model with the lowest mean RMSE is selected. The selected model is then evaluated on a held-out test set using MAE and R².

The trained model and related metadata are saved as:

```text
yield_model_bundle.joblib
```

---

## 3. System Architecture

```text
┌─────────────────────────────┐
│      Next.js Frontend       │
│                             │
│ Login / Dashboard / Report  │
└──────────────┬──────────────┘
               │
               │ HTTP / JSON
               ▼
┌─────────────────────────────┐
│       FastAPI Backend       │
│                             │
│   /api/agri-report          │
│   /api/countries            │
│   /health                   │
└──────────────┬──────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌───────────────┐  ┌─────────────────┐
│ ML Yield Model│  │   PostgreSQL    │
│               │  │    Database     │
│ Joblib Bundle │  │                 │
└───────────────┘  └─────────────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ Agricultural Data │
                 │ Weather / Soil    │
                 │ Fertilizer / CoP  │
                 │ Crop Prices       │
                 └───────────────────┘
```

---

## 4. Project Structure

A typical project layout is:

```text
Evergreen-Terran/
│
├── README.md
├── requirements.txt
├── db_engine.py
├── train_yield_model.py
├── yield_model_bundle.joblib
│
├── src/
│   ├── __init__.py
│   ├── backend_api.py
│   └── agri_core.py
│
└── final-agri-fin-frontend/
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── dashboard/
    │   │   └── page.tsx
    │   ├── report/
    │   │   └── page.tsx
    │   └── login/
    │       └── page.tsx
    │
    ├── public/
    │   ├── evergreen-logo.png
    │   └── evergreen terran background image.avif
    │
    ├── package.json
    ├── next.config.ts
    ├── next-env.d.ts
    └── tsconfig.json
```

> **Note:** The frontend files supplied for this README reference a `/login` route. Ensure that `app/login/page.tsx` exists in the final project.

---

## 5. Backend API

The FastAPI application provides the following endpoints.

### Root

```http
GET /
```

Example response:

```json
{
  "message": "Agri-Finance Backend is running"
}
```

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

### Generate Agricultural Finance Report

```http
POST /api/agri-report
```

Example request:

```json
{
  "farmer_name": "Ram",
  "country": "India",
  "crop": "Rice",
  "current_year": 2026,
  "farm_size_ha": 5,
  "loan_amount_usd": 20000,
  "annual_interest_rate": 12,
  "tenure_months": 12
}
```

Example response structure:

```json
{
  "report_text": "Generated agricultural finance report...",
  "summary": {
    "predicted_yield_ton_per_ha": 0,
    "total_production_tons": 0,
    "season_year": 0,
    "predicted_price_usd_per_ton": 0,
    "revenue_usd": 0,
    "total_cost_usd": 0,
    "profit_usd": 0,
    "capacity_ratio": 0,
    "decision_text": "",
    "price_crop": ""
  }
}
```

The numbers above are placeholders showing the response structure. Actual values are generated from the model and database.

### Available Countries

```http
GET /api/countries
```

This endpoint returns the combined list of countries available in the yield and cost-of-production datasets.

Example:

```json
{
  "countries": [
    "India",
    "Japan",
    "Thailand"
  ]
}
```

---

## 6. Database Requirements

Evergreen Terran uses **PostgreSQL**.

The application expects the following database objects to exist:

```text
yield_panel
crop_cop_per_ha
asia_wide_standardized_price_master final
```

### `yield_panel`

Used for machine-learning training and prediction context. It contains yield, weather, fertilizer, soil, country, crop, and year variables.

### `crop_cop_per_ha`

Used for cost-of-production calculations.

Expected fields include values for:

- country
- crop
- year
- fertilizer cost
- pesticide cost
- irrigation cost
- seed cost
- non-seed cost
- total cost per hectare

### `asia_wide_standardized_price_master final`

Used for crop-price forecasting.

The backend reads:

```text
crop_name
year
asia_price_usd_per_ton
```

---

## 7. Prerequisites

Before running the application, install:

- Python 3.10 or newer
- PostgreSQL
- Node.js
- npm
- Git (optional but recommended)

---

## 8. Backend Installation

### Step 1 — Open the project folder

```bash
cd Evergreen-Terran
```

### Step 2 — Create a virtual environment

Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Python packages

```bash
pip install -r requirements.txt
```

The backend requires packages including:

```text
fastapi
uvicorn
pydantic
pandas
numpy
scikit-learn
SQLAlchemy
joblib
xgboost
lightgbm
psycopg2-binary
```

If they are not already present in `requirements.txt`, install the missing packages:

```bash
pip install fastapi uvicorn pydantic numpy psycopg2-binary
```

---

## 9. Database Configuration

Do **not** store the PostgreSQL username/password directly in source code when sharing the project.

A recommended configuration is to use an environment variable.

Example `db_engine.py`:

```python
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not configured.")

engine = create_engine(DATABASE_URL)
```

Set the variable before starting the backend.

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://USERNAME:PASSWORD@localhost:5432/agri_fin_db"
```

Windows Command Prompt:

```cmd
set DATABASE_URL=postgresql+psycopg2://USERNAME:PASSWORD@localhost:5432/agri_fin_db
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql+psycopg2://USERNAME:PASSWORD@localhost:5432/agri_fin_db"
```

Replace:

```text
USERNAME
PASSWORD
agri_fin_db
```

with your own PostgreSQL configuration.

---

## 10. Training the Yield Model

Before using the backend, ensure the trained model bundle exists.

Run:

```bash
python train_yield_model.py
```

The training program:

1. Reads `yield_panel` from PostgreSQL
2. Selects numeric and categorical features
3. Creates a train/test split
4. Evaluates multiple regression algorithms
5. Performs 5-fold cross-validation
6. Selects the model with the lowest average RMSE
7. Evaluates the selected model using MAE and R²
8. Saves the trained model and metadata

Output:

```text
yield_model_bundle.joblib
```

The backend loads this file when `agri_core.py` is imported.

---

## 11. Running the FastAPI Backend

From the main project folder, run:

```bash
uvicorn src.backend_api:app --reload --host 127.0.0.1 --port 8000
```

The backend should be available at:

```text
http://127.0.0.1:8000
```

Interactive Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

---

## 12. Frontend Installation

Open a second terminal.

Move to the frontend directory:

```bash
cd final-agri-fin-frontend
```

Install dependencies:

```bash
npm install
```

---

## 13. Frontend Environment Configuration

The frontend uses:

```text
NEXT_PUBLIC_BACKEND_URL
```

If this variable is not configured, the application defaults to:

```text
http://127.0.0.1:8000
```

You can create:

```text
.env.local
```

inside `final-agri-fin-frontend/`.

Example:

```env
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
```

Do not commit secret credentials to `.env.local`.

---

## 14. Running the Next.js Frontend

Start the development server:

```bash
npm run dev
```

The application normally opens at:

```text
http://localhost:3000
```

Available npm commands are:

```bash
npm run dev
npm run build
npm run start
npm run lint
```

---

## 15. CORS Configuration

The FastAPI backend currently allows frontend requests from:

```text
http://localhost:3000
http://127.0.0.1:3000
```

If the frontend is deployed to another host or port, update the CORS configuration in `backend_api.py`.

---

## 16. Application Workflow

The main application flow is:

```text
User opens application
        │
        ▼
Authentication check
        │
        ▼
Bank Officer Dashboard
        │
        ▼
Enter farmer, crop and loan information
        │
        ▼
Frontend calculates approximate EMI
        │
        ▼
POST /api/agri-report
        │
        ▼
FastAPI calls generate_agri_finance_report()
        │
        ├── Predict crop yield
        ├── Forecast crop price
        ├── Retrieve production cost
        ├── Estimate expected production
        ├── Calculate revenue
        ├── Calculate expected profit
        └── Calculate repayment-capacity ratio
        │
        ▼
JSON response returned to frontend
        │
        ▼
Farmer Loan Assessment Report
        │
        ▼
Print / Save as PDF
```

---

## 17. Frontend Pages

### Home Page

The root page checks a simple authentication flag stored in browser local storage:

```text
evergreen_auth
```

If authenticated, the user is redirected to:

```text
/dashboard
```

Otherwise, the user is redirected to:

```text
/login
```

### Officer Dashboard

The dashboard allows the officer to enter:

- Farmer name
- Country
- Crop
- Current year
- Farm size
- Loan amount
- Annual interest rate
- Loan tenure

The page calculates an approximate EMI and total payable amount.

When the form is submitted, the information is sent to the backend and the user is redirected to the report page.

### Report Page

The report page requests the agricultural finance prediction from FastAPI and displays:

- Farmer details
- Loan details
- Repayment summary
- Officer remarks section
- Predicted agricultural-finance summary
- Farmer acknowledgement
- Bank-officer signature section

The page includes a **Print / Save PDF** button.

---

## 18. Machine-Learning Workflow

The yield-model training pipeline uses a `ColumnTransformer`.

Numeric variables are passed directly to the selected regression algorithm.

Categorical variables:

```text
country
crop
```

are transformed with:

```text
OneHotEncoder(handle_unknown="ignore")
```

Candidate models are evaluated using:

```text
5-fold cross-validation
```

with negative mean squared error as the scoring metric. RMSE is calculated from the cross-validation scores.

The best pipeline is saved with metadata including:

- Selected model
- Model evaluation metrics
- Global numeric means
- Numeric feature names
- Categorical feature names
- Supported yield countries
- Supported crops

---

## 19. Price Forecast Method

For the selected crop, the system:

1. Retrieves historical Asia-wide crop prices up to the selected year
2. Uses up to seven of the most recent observations
3. Calculates a compound annual growth rate
4. Limits the annual rate to between -5% and +5%
5. Produces prices for the next five years

This is a constrained trend-based forecasting method and should not be interpreted as a guaranteed future market price.

---

## 20. Cost-of-Production Method

The system searches the cost-of-production dataset for the selected country and crop.

If the exact requested year is unavailable, the nearest available year is used.

The system calculates:

```text
Total Farm Cost = Cost per Hectare × Farm Size
```

The cost breakdown includes fertilizer, pesticides, irrigation, seeds, and other costs where available.

---

## 21. Important Limitations

Evergreen Terran is a research prototype and decision-support system.

Important limitations include:

- Predictions depend on the quality and coverage of the source datasets.
- Crop-price forecasts use historical growth rather than a dedicated econometric or deep-learning forecasting model.
- Future weather conditions are not directly forecast by the current yield-prediction process.
- The yield model uses recent historical environmental values when preparing future prediction inputs.
- Cost-of-production calculations can use the nearest available year when the requested year is unavailable.
- The loan-risk decision is based on estimated profit relative to repayment obligations and is not a substitute for a complete institutional credit-risk model.
- Historical borrower repayment behavior, credit score, collateral quality, household liabilities, and other banking variables are not included.
- EMI shown by the frontend and repayment calculations used by the backend follow different calculation conventions: the frontend uses a reducing-balance EMI formula, while the backend repayment-capacity calculation uses simple interest.
- The current frontend authentication mechanism uses browser local storage and is intended for demonstration purposes rather than production security.

---

## 22. Security Notes

Before uploading this project to GitHub or sharing it publicly:

- Remove database passwords from source files
- Use environment variables for database credentials
- Do not commit `.env` or `.env.local`
- Do not upload private API keys
- Do not upload PostgreSQL backups containing sensitive information
- Do not commit `node_modules`
- Do not commit Python virtual environments
- Use proper server-side authentication before production deployment

A recommended `.gitignore` should include:

```gitignore
# Python
venv/
.venv/
__pycache__/
*.pyc

# Environment variables
.env
.env.*
!.env.example

# Next.js
node_modules/
.next/
out/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

## 23. Troubleshooting

### Frontend shows "Failed to fetch"

Check that the FastAPI backend is running:

```bash
uvicorn src.backend_api:app --reload --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

Also verify:

```env
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
```

### PostgreSQL connection error

Check:

- PostgreSQL is running
- Database name is correct
- Username and password are correct
- `DATABASE_URL` is configured
- `psycopg2-binary` is installed

### `yield_model_bundle.joblib` not found

Run:

```bash
python train_yield_model.py
```

and ensure the generated file is located where `agri_core.py` expects it.

### Country or crop not found

The backend performs case-insensitive exact, prefix, and substring matching, but the requested country and crop must still be represented in the relevant datasets.

### Next.js page redirects to `/login`

The frontend checks:

```text
localStorage["evergreen_auth"]
```

Ensure the login page sets this value to:

```text
true
```

after successful demo authentication.

---

## 24. Development Commands

### Backend

Activate the Python environment:

```bash
venv\Scripts\activate
```

Start FastAPI:

```bash
uvicorn src.backend_api:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd final-agri-fin-frontend
npm run dev
```

### Stop Development Servers

In the relevant terminal:

```text
Ctrl + C
```

---

## 25. Intended Use

Evergreen Terran is intended as an agricultural financial-planning and decision-support prototype.

It demonstrates how heterogeneous agricultural datasets and machine-learning methods can be integrated with financial calculations to support agricultural loan appraisal.

The application is not intended to provide automatic final loan approval and should not replace professional financial, agricultural, or banking judgement.

---

## 26. Author

**Omkar Jotiram Katkar**

M.Sc. Data Science  
University of Europe for Applied Sciences

Master's Thesis Project

**Project:** Evergreen Terran — A Data-Driven Web Application for Agricultural Financial Planning and Risk Analysis

---

## 27. License

This project was developed for academic and research purposes.

Unless a separate license is added, all rights remain with the author.

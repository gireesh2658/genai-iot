# IoTSynth AI

**Synthetic IoT Device Traffic Generator for Anomaly Detection**

IoTSynth AI generates domain-valid synthetic IoT network telemetry across diverse IoT hardware device types and cyberattack classes to benchmark and augment anomaly-detection pipelines (`TRTR`, `TSTR`, and `TSTR+R`).

---

## Architecture Overview

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js 14, React, TypeScript | Signal Intelligence Studio web application (`/`, `/studio`, `/quality`, `/anomaly`) |
| **Backend API** | FastAPI, Python 3.12 | Versioned REST endpoints (`/api/v1`) for synthesis, vault exports, statistical audits, and ML scoring |
| **Generative Engine** | SDV CTGAN (`0.13.0` / `2.2.0`) | Pre-trained tabular conditional synthesis serving `v2` (primary) and `v1` (baseline) |
| **Anomaly Detection** | Scikit-learn (`1.9.1`) | 20 pre-trained baseline pipelines (`RandomForest`, `ExtraTrees`, `HistGradientBoosting`, `LogisticRegression`) plus custom training |
| **Domain Engine** | CICIoT2023 Schema | Canonical flow schema, deterministic protocol/label validation, and variance/bounds integrity |

---

## Pre-Trained Generative Models

Both packaged checkpoints execute strictly in inference mode; synthetic traffic generation never initiates model training.

| Model Identifier | Role | Checkpoint Path | Specification |
| :--- | :--- | :--- | :--- |
| `ctgan_device_aware_v2` | **Primary Default** | `models/ctgan/v2/ctgan_device_aware_v2.pkl` | Native device-aware conditional CTGAN across `70` pseudonymized physical IoT devices (`device_001`–`device_070`) and `7` device categories (`7` discrete columns, `108`-dim conditional vector; trained offline on RTX 3050 GPU, served on CPU) |
| `ctgan_full_v1` | **Retained Baseline** | `models/ctgan/v1/ctgan_full_v1.pkl` | Original `25`-discrete-column baseline model preserved for V1-vs-V2 comparison and optional profile calibration |

V2 device conditioning metadata is served from the MAC/IP-free catalog in `models/ctgan/v2/ctgan_device_aware_v2_device_catalog.json`.

---

## Repository Structure

```text
.
├── anomaly_detection/       # ML data loaders, evaluators, 20 baseline .joblib pipelines, and result JSONs
├── backend/                 # FastAPI entrypoint, env-driven config, routes, Pydantic schemas, and services
├── datasets/
│   ├── generated/           # Protected V1 baseline sample parquets & sidecar metadata
│   └── processed/           # Preprocessed CICIoT2023 reference parquet sample
├── frontend/                # Next.js 14 App Router UI
├── models/ctgan/            # Preserved v1 and primary v2 checkpoints, configs, metadata, and V2 catalog
├── reports/
│   ├── ctgan_v2/            # V2 evaluation, device coverage, and V1-vs-V2 benchmark JSONs
│   └── phase6/              # Baseline CTGAN statistical fidelity & domain validity reports
├── scripts/
│   ├── start_backend.ps1    # Local CPU FastAPI launcher
│   ├── start_frontend.ps1   # Local Next.js launcher
│   └── pipeline/            # Offline CLI scripts for data prep, GPU training, and benchmarking
├── simulator/               # Canonical feature schema, 6 empirical device profiles, 33 attack signatures
├── synthetic_engine/        # CTGAN model wrapper, feature encoding, repair, and statistical evaluators
├── .env.example             # Environment variable template
├── render.yaml              # Render two-service Blueprint configuration
├── requirements.txt         # Local CPU backend dependencies
├── requirements-render.txt  # Lean CPU production dependencies for Render
└── requirements-gpu.txt     # Optional local CUDA dependencies for offline GPU scripts
```

---

## Local Setup & Quickstart

**Prerequisites:** Python `3.12+` and Node.js `18+` (`20 LTS` recommended).

### 1. Backend Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Frontend Build
```powershell
cd frontend
npm ci
npm run build
cd ..
```

### 3. Launch Services
Run each server in its own terminal:
```powershell
# Terminal 1 — FastAPI Backend (http://127.0.0.1:8000)
.\scripts\start_backend.ps1

# Terminal 2 — Next.js Frontend (http://127.0.0.1:3000)
.\scripts\start_frontend.ps1
```

* **Executive Workbench:** `http://localhost:3000/`
* **Synthetic Data Studio:** `http://localhost:3000/studio`
* **Quality Audit:** `http://localhost:3000/quality`
* **Anomaly Detection Lab:** `http://localhost:3000/anomaly`
* **Swagger API Docs:** `http://localhost:8000/docs`

---

## Render Production Deployment

The included `render.yaml` Blueprint defines two coordinated Render Web Services:

| Service | Runtime | Root Dir | Build Command | Start Command |
| :--- | :--- | :--- | :--- | :--- |
| `iotsynth-ai-backend` | Python (`3.12.10`) | `.` | `pip install --upgrade pip && pip install -r requirements-render.txt` | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| `iotsynth-ai-frontend` | Node (`20`) | `frontend` | `npm ci && npm run build` | `npm run start -- --hostname 0.0.0.0 --port $PORT` |

### Required Cross-Service Environment Variables
1. Deploy `iotsynth-ai-backend` and note its public HTTPS URL (e.g., `https://iotsynth-ai-backend.onrender.com`).
2. On `iotsynth-ai-frontend`, set `NEXT_PUBLIC_BACKEND_URL` to the backend URL and rebuild so browser requests target the live backend directly.
3. On `iotsynth-ai-backend`, set `CORS_ORIGINS` to the deployed frontend URL (e.g., `https://iotsynth-ai-frontend.onrender.com`).

---

## Deployment Notes

* **Ephemeral Server Exports:** Runtime exports on Render write to `IOTSYNTH_GENERATED_DIR=/tmp/iotsynth_generated` (instance-scoped storage), while bundled baseline datasets remain available across restarts and the Studio UI also provides direct browser CSV export without server persistence.
* **Portable CPU Serving:** Production serving runs CPU PyTorch inference (`requirements-render.txt`) and uses an instance with sufficient memory (2 GB+ RAM recommended when loading CTGAN checkpoints alongside Scikit-learn detectors).

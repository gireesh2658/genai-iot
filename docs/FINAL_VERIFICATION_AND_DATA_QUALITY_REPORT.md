# IoTSynth AI — Final Verification & Synthetic Data Quality Report

## 1. Runtime & Model Upgrade Summary

| Item | Verified State |
|---|---|
| **1. Original Node.js Configuration** | `render.yaml` (`iotsynth-ai-frontend`): `NODE_VERSION: "20"`. No `.node-version`, `.nvmrc`, or `engines.node`. |
| **2. New Node.js Configuration** | `frontend/.node-version` (`26.13.1`), `frontend/.nvmrc` (`26.13.1`), `frontend/package.json` (`"engines": { "node": ">=26.13.1 <27" }`, `@types/node@^26.6.11`), and `render.yaml` (`iotsynth-ai-frontend` ONLY `NODE_VERSION: "26.13.1"`). |
| **3. Actual Runtime Selected** | **Node.js `v26.13.1` LTS ("Lithium")** (`npm 11.20.0`) exclusively for Next.js `16.4.6`. Python `3.12.10` FastAPI ML backend (`FastAPI 0.163.0`, `PyTorch 2.15.0+cpu`, `SDV 2.2.0`, `CTGAN 0.13.0`) preserved in `.venv` (`CUDA 13.0` `.venv-gpu` for RTX 3050 training). |
| **4. Compatibility Findings** | `npm run lint` (`next typegen && tsc --noEmit`) & `npm run build` (`Next.js 16.4.6` Turbopack) exited `0` (`npm audit`: `0 vulnerabilities`). |
| **5. Generative Model Upgrade** | Re-trained `ctgan_device_aware_v2` on RTX 3050 GPU (`150` epochs, `batch_size=1000`, `14` `log1p`-compressed heavy-tailed columns) in **`875.53s`** (`100.44 MB` peak VRAM; `6.89x` faster than V1), serialized CPU-portable cleanly (`8,382,530` bytes). |

## 2. Files Modified

- `gen_AI_project/frontend/.node-version`, `frontend/.nvmrc`, `frontend/package.json`, `frontend/package-lock.json`, `render.yaml` (`iotsynth-ai-frontend` only).
- `gen_AI_project/frontend/src/app/globals.css`, `FlowDataTable.tsx`, `ValidationPanel.tsx`, `frontend/src/app/studio/page.tsx`, plus simplified `/studio` consolidation + HTTP `307` redirects from `/`, `/quality`, `/anomaly`.
- `gen_AI_project/synthetic_engine/ctgan_v2_pipeline.py` & `ctgan_model.py` — added training-bounded `log1p`/`expm1` compression & inversion cleanly inside `CTGANModel.sample()`.
- `gen_AI_project/scripts/pipeline/train_ctgan_v2.py` & `evaluate_ctgan_v2.py` — GPU `log1p` training and evaluation wrapper alignment.
- `gen_AI_project/backend/services/ctgan_service.py` — added category->`device_id` consistency normalization (`67% -> 100%`) and `TCP`/`UDP` dual-flag mutual exclusion.
- `gen_AI_project/backend/services/evaluation_service.py` — registered `ciciot2023_device_v2_train` (`88,146`-row V2 corpus) alongside `ciciot2023_preprocessed_sample`.

## 3. Live Chrome Desktop Verification (`1280x850`)

- **Routes Inspected**: `http://127.0.0.1:3000/studio` (plus HTTP `307` redirects from `/`, `/quality`, `/anomaly`): **0 console errors**, **0 HTTP 4xx/5xx responses**, **0 DevTools accessibility issues**.
- **Generation Parameters (`iot_synthetic_v2_20261126_025006`)**: `ctgan_device_aware_v2`, Category `Camera`, Device `Any Camera Device (17 devices)`, `Balanced Mix` + `Boost rare attack classes`, `500` rows, `Enforce Domain Consistency = true`.
- **Generated Record Count & Timing**: **`500` rows × `44` columns** generated in **`12.784s`** (`Spoofing: 88`, `Reconnaissance: 87`, `Benign: 75`, `Mirai: 56`, `DDoS: 56`, `DoS: 56`, `Web-based: 44`, `Brute Force: 38`).
- **Generated File References & Export Parity**:
  - `datasets/generated/iot_synthetic_v2_20261126_025006.{csv,parquet,_metadata.json}`
  - `%USERPROFILE%\Downloads\iot_synthetic_v2_20261126_025006.csv` (`218,213` bytes) and `.parquet` (`133,985` bytes) — **100% SHA-256 identical** to server files.

## 4. Synthetic Data Quality & Utility Results

- **Structural & Device/Label Correctness (`iot_synthetic_v2_20261126_025006`)**:
  - `500/500` (`100%`) finite, `0` nulls, `0` infinities, `0` negative values, `0` duplicate rows, `0` raw MAC/IP leakage.
  - `0` label/category/`is_attack`/IANA protocol/`Std=sqrt(Variance)` violations post-repair.
  - **`500/500` (`100.0%`) true Camera `device_id`s** (`device_016..device_032`) — improved from `67.0%`.
  - **`0/500` (`0.0%`) simultaneous `TCP=1 & UDP=1` contradictions** — improved from `1.25%`.
  - Intentional unclamped caveats retained: `217` bound-check flags across `Min <= AVG <= Max` (`189` rows clean-check count) and `205/500` (`41.0%`) `AVG` vs `Tot sum / Number` >10% deviations (down from `64.75%`).
- **Statistical Similarity (`eval_20261126_025049_08180e` vs `ciciot2023_device_v2_train`)**:
  - Mean KS **`0.2802`** (down from `0.5255`), Mean JS **`0.3669`** (down from `0.5572`), Wasserstein (`W1`) **`2666.72`** (down from `6766.99`), Pearson MACE **`0.1189`** (down from `0.1607`), Spearman MACE **`0.1386`** (down from `0.2493`), Exact Train Overlaps **`0 rows`**, Min 1-NN **`0.0045`** (Median **`0.4745`**, P95 **`1.9258`**).
  - Unconditioned V2 6,000-row benchmark (`quality_report.json`): Mean KS **`0.2842`**, Mean JSD **`0.3443`**, Pearson MACE **`0.0814`** (`Frobenius 1.3246`), Spearman MACE **`0.1220`** (`Frobenius 1.8238`), Exact Train Overlaps **`0`**.
- **Downstream Anomaly-Detection Utility (`anomaly_utility_report.json` on `18,889` real test flows)**:
  - `TSTR_v2_repaired` improved across every classifier: Random Forest Macro-F1 **`0.5271`** (up from `0.5032`; Acc **`0.5115`**), Extra Trees **`0.5033`** (`0.4972`), HistGradientBoosting **`0.5160`** (`0.5079`), Logistic Regression **`0.4481`** (`0.4458`).
  - `TSTR+R`: Random Forest achieves **`0.7217`** (`25%`) and **`0.7228`** (`50%`, Acc **`0.7304`**) vs `TRTR` **`0.7154`**; HistGradientBoosting **`0.7052`** (`25%`) vs `0.7025`; Extra Trees (`0.6703` vs `0.6833`) and Logistic Regression (`0.5281` vs `0.5564`) decline slightly vs TRTR.

## 5. Evidence Screenshots & Verification Matrix

- **Desktop Chrome Screenshots (`docs/evidence/browser/`)**: `02-studio-initial.png`, `03-device-selection.png`, `04-generation-configured.png`, `05-generation-and-preview.png`, `06b-flow-inspector-drawer.png`, `07-quality-results.png`, `08-export-controls.png` *(mobile and outdated Render captures excluded)*.

| Verification Area | Status | Scope & Notes |
|---|---|---|
| Node.js `v26.13.1` LTS Upgrade & `Next.js 16.4.6` Build | **Verified** | Local frontend lint, TypeScript check, build, and `npm audit` (`0` issues). |
| Log1p GPU Training (`875.53s`) & V2 Benchmark (`evaluate_ctgan_v2.py`) | **Verified** | RTX 3050 CUDA 13.0 training + CPU portability + full quality/utility JSONs. |
| Real Chrome Desktop Workflow (`/studio` + CSV/Parquet + Audit) | **Verified** | `iot_synthetic_v2_20261126_025006` + `eval_20261126_025049_08180e`, `0` errors. |
| Category->`device_id` (`100%`) & `TCP/UDP` (`0` contradictions) | **Verified** | Verified directly on Chrome-downloaded Parquet/CSV files (`500/500`). |
| Unclamped Arithmetic Heuristics (`Min<=AVG<=Max`, `AVG~TotSum/N`) | **Intentional Partial** | Left unclamped (`41.0%` quotient deviation) to protect marginal KS fidelity. |
| Production Render Redeployment | **Not Pushed** | Local upgraded build & model checkpoint not pushed to GitHub/Render. |

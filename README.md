# 🌙 LunaAstra — Lunar Habitat AI Decision Support System

An AI-powered decision support system that identifies optimal locations for long-term human habitats on the Moon by fusing real NASA/ISRO satellite datasets into a scored, ranked, and fully explainable tool with a 3D interactive Moon globe.

---

## Core Factors Analyzed

| Factor | Dataset Source | Direction |
|---|---|---|
| Water Ice Availability | LEND (ISRO Chandrayaan) | Higher = Better |
| Solar Illumination | Diviner (LRO) | Higher = Better |
| Radiation Safety | CRaTER (LRO) | Lower = Better |
| Terrain Suitability | LOLA DEM (LRO) | Lower slope = Better |
| Earth Comm Visibility | Geometric model | Higher = Better |

---

## Tech Stack

- **Desktop Shell:** Electron
- **Frontend:** React + CesiumJS + Recharts
- **Backend:** FastAPI (Python), spawned as local subprocess
- **Geospatial:** Rasterio + GDAL + Xarray + Dask
- **Database:** SQLite + SpatiaLite
- **AI:** Claude API (NL assistant + XAI narration)
- **Space Weather:** NASA DONKI API (live radiation alerts)

---

## Project Structure

```
LunaAstra-WSM/
├── backend/          # FastAPI Python backend
├── frontend/         # Electron + React frontend
└── docs/             # Architecture & data documentation
```

---

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/score` | Score all pixels, return heatmap + top N sites with XAI |
| POST | `/explain/site` | Full XAI report for one site (Claude briefing) |
| POST | `/explain/compare` | What-if scenario comparison with Claude narration |
| GET | `/explain/report/{site_id}` | Exportable site report |
| POST | `/assistant` | Natural language → weight JSON (Claude) |
| GET | `/space-weather` | Live solar activity alert level |

---

## Explainable AI Architecture

```
Core Scorer (NumPy, deterministic)
    ↓
XAI Explainer Layer
  ├── Contribution Breakdown  (weight × score per factor)
  ├── Risk Profile Labels     (LOW / MEDIUM / HIGH per factor)
  ├── Ice Detection Confidence (rule-based, 0–100%)
  └── Claude Narration Engine (site briefing, scenario diff)
    ↓
Frontend: Risk badges, mission briefing, Recharts breakdown
```

> The core scoring math is fully deterministic and auditable.
> Claude is used only for natural language I/O, never for scoring decisions.

---


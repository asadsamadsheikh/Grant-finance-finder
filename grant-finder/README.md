# 🚀 GrantAI — AI Grant & Funding Finder for Startups
### Problem Statement #18 | IBM Cloud Lite + IBM Granite (watsonx.ai)

<div align="center">

![IBM Granite](https://img.shields.io/badge/IBM-Granite%203%208B-0f62fe?logo=ibm&logoColor=white)
![watsonx.ai](https://img.shields.io/badge/IBM-watsonx.ai-6929c4?logo=ibm&logoColor=white)
![Watson NLU](https://img.shields.io/badge/IBM-Watson%20NLU-1192e8?logo=ibm&logoColor=white)
![IBM COS](https://img.shields.io/badge/IBM-Cloud%20Object%20Storage-0e62fe?logo=ibm&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)

**Intelligent grant discovery, multi-layer eligibility matching, and full proposal generation — powered entirely by IBM Cloud Lite (free tier) services.**

</div>

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GrantAI Platform                         │
├──────────────────────────┬──────────────────────────────────────┤
│   Frontend (Vanilla JS)  │        FastAPI Backend               │
│   IBM Carbon Design UI   │                                      │
│   ┌──────────────────┐   │  ┌────────────────────────────────┐  │
│   │ Startup Profile  │───┼─▶│  /api/grants/search            │  │
│   │ Form             │   │  │  Eligibility Matcher           │  │
│   └──────────────────┘   │  │  ┌──────────────────────────┐  │  │
│   ┌──────────────────┐   │  │  │ Layer 1: Rule Filter      │  │  │
│   │ Results Panel    │◀──┼──│  │ Layer 2: IBM Watson NLU   │  │  │
│   │ (scored grants)  │   │  │  │ Layer 3: IBM Granite LLM  │  │  │
│   └──────────────────┘   │  │  └──────────────────────────┘  │  │
│   ┌──────────────────┐   │  └────────────────────────────────┘  │
│   │ Proposal Editor  │◀──┼─▶  /api/proposals/generate          │  │
│   └──────────────────┘   │      IBM Granite Proposal Writer     │  │
└──────────────────────────┴──────────────────────────────────────┘
                                        │
               ┌────────────────────────┼────────────────────┐
               ▼                        ▼                    ▼
     IBM watsonx.ai           IBM Watson NLU       IBM Cloud Object
     Granite 3-8B             (NER, Keywords)      Storage (Cache)
     (LLM Reasoning)          Lite – FREE          Lite – FREE
     Lite – FREE
```

## ✨ Unique Features

| Feature | Description |
|---|---|
| **3-Layer AI Matching** | Rule-based → IBM Watson NLU keyword scoring → IBM Granite deep reasoning |
| **IBM Granite Proposals** | Full 8-section grant proposals generated in <60s using few-shot prompting |
| **Multi-Source Aggregation** | Curated DB (12 grants) + live Grants.gov API + expandable to SAM.gov |
| **IBM COS Persistent Cache** | Generated proposals stored in IBM Cloud Object Storage for retrieval |
| **Zero-Config Fallback** | Runs fully without API keys using curated DB + keyword matching |
| **IBM Carbon UI** | Professional IBM Carbon Design System inspired interface |
| **Proposal Export** | Download proposals as plain text or copy to clipboard |
| **Global Coverage** | USA (NSF, DOE), EU (EIC, Climate-KIC), India (DPIIT, SIDBI), Global (YC, Techstars) |

---

## 📦 What to Install / Download

### 1. Python (v3.11 or higher)
**Download:** https://www.python.org/downloads/
```bash
# Verify installation
python --version   # Should show 3.11.x or higher
```

### 2. Git (for cloning)
**Download:** https://git-scm.com/downloads

### 3. Python Packages (auto-installed via requirements.txt)
```
fastapi          — Web framework
uvicorn          — ASGI server
httpx            — Async HTTP client (IBM API calls)
pydantic         — Data validation
python-dotenv    — .env file loading
ibm-watson       — IBM Watson NLU SDK
ibm-cos-sdk      — IBM Cloud Object Storage SDK
ibm-cloud-sdk-core — IBM Cloud authentication
```

---

## 🔧 IBM Cloud Setup (All FREE — Lite Plan)

### Step 1: Create IBM Cloud Account (FREE)
1. Go to **https://cloud.ibm.com/registration**
2. Sign up with email — no credit card required for Lite plan
3. Verify your email

### Step 2: IBM watsonx.ai (Granite LLM)
1. Login → **https://dataplatform.cloud.ibm.com**
2. Click **"New project"** → Name it `grant-finder`
3. Go to **Manage → Access Control → API Keys → New API key**
4. Copy your **API Key** → Set as `IBM_WATSONX_API_KEY`
5. Go to project **Settings → General** → Copy **Project ID** → Set as `IBM_WATSONX_PROJECT_ID`

> ℹ️ **Lite Plan includes:** 50,000 free tokens/month on Granite models

### Step 3: IBM Watson Natural Language Understanding (NLU)
1. IBM Cloud Catalog → Search **"Natural Language Understanding"**
2. Select **Lite plan** → Create instance
3. Go to **Manage → Credentials → New credential** → Copy API key
4. Copy the **Service URL** from same page
5. Set `IBM_NLU_API_KEY` and `IBM_NLU_URL` in `.env`

> ℹ️ **Lite Plan includes:** 30,000 NLU items/month FREE

### Step 4: IBM Cloud Object Storage (COS)
1. IBM Cloud Catalog → Search **"Object Storage"**
2. Select **Lite plan** → Create instance
3. Click your instance → **Service credentials → New credential** (enable HMAC)
4. Create a **bucket** named `grant-finder-cache` in region `us-south`
5. Copy **Resource instance CRN** from instance details
6. Set `IBM_COS_API_KEY`, `IBM_COS_INSTANCE_CRN` in `.env`

> ℹ️ **Lite Plan includes:** 25 GB storage + 20 GB outbound FREE

### Step 5 (Optional): SAM.gov API (US Grants)
1. Go to **https://open.gsa.gov/api/sam/** 
2. Register for a free API key
3. Set as `SAM_GOV_API_KEY` in `.env`

---

## ⚡ Quick Start

```bash
# 1. Clone the project
git clone <repo-url>
cd grant-finder

# 2. Create virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy env.example .env        # Windows
# cp env.example .env        # macOS/Linux

# 5. Edit .env with your IBM credentials
# (See IBM Cloud Setup section above)
notepad .env                 # Windows
# nano .env                  # macOS/Linux

# 6. Run the server
python main.py

# Or with uvicorn directly:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Open:** http://localhost:8000

**API Docs:** http://localhost:8000/api/docs

---

## 📁 Project Structure

```
grant-finder/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── env.example                      # Environment variable template
│
├── backend/
│   ├── services/
│   │   ├── granite_service.py       # IBM Granite (watsonx.ai) integration
│   │   ├── nlu_service.py           # IBM Watson NLU integration
│   │   ├── cos_cache.py             # IBM Cloud Object Storage cache
│   │   ├── grant_aggregator.py      # Multi-source grant data fetcher
│   │   ├── eligibility_matcher.py   # 3-layer AI matching engine
│   │   └── proposal_generator.py    # IBM Granite proposal writer
│   ├── routes/
│   │   ├── grants.py                # Grant search API endpoints
│   │   └── proposals.py             # Proposal generation endpoints
│   └── models/
│       └── schemas.py               # Pydantic request/response models
│
└── frontend/
    ├── index.html                   # Single-page application
    ├── css/style.css                # IBM Carbon-inspired styles
    └── js/app.js                    # Frontend JavaScript
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/grants/search` | AI-powered grant matching for startup profile |
| `GET`  | `/api/grants/all` | List all grants in curated database |
| `GET`  | `/api/grants/{id}` | Get specific grant details |
| `POST` | `/api/proposals/generate` | Generate full proposal via IBM Granite |
| `GET`  | `/api/proposals/{id}` | Retrieve saved proposal from IBM COS |
| `GET`  | `/api/health` | IBM service configuration status |
| `GET`  | `/api/docs` | Interactive Swagger UI |

### Sample Request — Grant Search
```bash
curl -X POST http://localhost:8000/api/grants/search \
  -H "Content-Type: application/json" \
  -d '{
    "startup_profile": {
      "name": "ClimateAI Labs",
      "description": "We build AI-powered carbon accounting for SMEs",
      "industry": "climate tech",
      "stage": "seed",
      "location": "USA",
      "keywords": ["AI", "carbon", "sustainability", "SaaS"]
    },
    "max_results": 5,
    "use_granite_analysis": true
  }'
```

---

## 🧠 How the AI Matching Works

```
Startup Profile Input
        │
        ▼
┌──────────────────────┐
│  Layer 1: Rule Filter │  ← Stage + Location hard filters
└──────────┬───────────┘
           │ (pre-filtered grants)
           ▼
┌──────────────────────────────┐
│  Layer 2: IBM Watson NLU     │  ← Keyword extraction + Jaccard similarity
│  Keyword Scoring (0-60 pts)  │    Industry alias expansion
└──────────┬───────────────────┘    Boost for high-value tech terms
           │ (top 8 scored grants)
           ▼
┌─────────────────────────────────────────────────────┐
│  Layer 3: IBM Granite 3-8B Deep Analysis (Top 3)    │
│  - Eligibility assessment via structured prompting  │
│  - Matched/missing criteria extraction              │
│  - Confidence-weighted score blending (40/60 mix)   │
└─────────────────────────────────────────────────────┘
           │
           ▼
     Ranked Results with:
     • Match score (0-100)
     • IBM Granite recommendation
     • Matched criteria
     • Missing criteria
     • Risk level
```

## 📝 IBM Granite Proposal Sections Generated

1. **Executive Summary** — 150-200 words
2. **Problem Statement** — 200-250 words  
3. **Proposed Solution** — 250-300 words
4. **Innovation & Uniqueness** — 200 words
5. **Team Qualifications** — 180 words
6. **Implementation Plan** — 12-month phased plan
7. **Expected Outcomes & Impact** — 5-6 measurable KPIs
8. **Budget Outline** — Categorized breakdown with percentages
9. **Cover Letter** *(optional)* — 3-paragraph professional letter

> ⚠️ All AI-generated proposals require human review before submission.

---

## 🌍 Grant Database Coverage

| Grant | Funder | Region | Amount | Type |
|---|---|---|---|---|
| NSF SBIR Phase I | NSF | USA | Up to $275K | Grant |
| DOE SBIR Phase I | Dept. of Energy | USA | $200K | Grant |
| Y Combinator W2025 | Y Combinator | Global | $500K | Equity |
| EIC Accelerator | EU Commission | EU/EEA | €500K–€2.5M | Grant |
| Gates Grand Challenges | Gates Foundation | Global | $100K | Grant |
| Startup India SISFS | DPIIT India | India | ₹20L–₹50L | Grant |
| AWS Activate | Amazon | Global | $5K–$100K | Credits |
| Google Black Founders Fund | Google | USA/UK/BR | $50K–$100K | Grant |
| Techstars Accelerator | Techstars | Global | $120K | Equity |
| EIT Climate-KIC Launchpad | EIT EU | EU | €5K–€95K | Grant |
| Microsoft Founders Hub | Microsoft | Global | Up to $150K | Credits |
| SIDBI Fund of Funds | SIDBI India | India | $500K–$5M | Equity |

---

## ⚖️ Legal & Compliance Notes

- Only uses **public APIs and datasets** — no scraping of restricted portals
- Respects Grants.gov and SAM.gov terms of service
- All proposals are clearly marked as **AI-generated drafts**
- Users are responsible for verifying eligibility before submission
- No confidential funder data is stored or transmitted

---

## 🛠️ Troubleshooting

| Issue | Solution |
|---|---|
| `IBM_WATSONX_API_KEY not working` | Ensure key has `watsonx` IAM role; check project ID matches |
| `NLU returning 401` | Verify key format: no spaces, correct instance URL |
| `COS bucket not found` | Create bucket named exactly `grant-finder-cache` in us-south |
| `Backend offline` | Check `python main.py` is running; default port 8000 |
| Slow response | Disable "IBM Granite analysis" toggle for faster keyword-only results |

---

<div align="center">
Built with ❤️ using IBM Cloud Lite — Problem Statement #18
<br/>
<strong>IBM Granite</strong> (watsonx.ai) · <strong>Watson NLU</strong> · <strong>IBM Cloud Object Storage</strong>
</div>

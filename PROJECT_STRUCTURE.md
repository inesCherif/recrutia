# Recrutia — Project Structure

```
Recrutia/
├── agents/                     # AI Agent logic
│   ├── core/                   # Shared orchestrator + comprehension
│   │   ├── orchestrator.py     # Request routing & coordination
│   │   ├── comprehension/      # NLU / intent detection
│   │   └── audio/              # Voice processing
│   ├── student/                # Candidate-side agents
│   │   ├── multi_agent_system.py   # 7 AI agents (CV Analyzer, Matcher, Writer, etc.)
│   │   ├── matcher_fix.py      # Scoring patches
│   │   ├── agent_student.py    # Student orchestrator
│   │   ├── agent_linkedin_search.py
│   │   └── tools/
│   │       └── job_scraper.py  # 11-source job scraper (LinkedIn, Indeed, etc.)
│   └── entrepreneur/           # Recruiter-side agents
│       ├── recruiter_agents.py # Job posting generation, candidate scoring
│       ├── agent_entrepreneur.py
│       ├── agent_linkedin_post.py
│       ├── analysis/
│       └── communication/
│
├── backend/                    # FastAPI server
│   ├── main.py                 # App entrypoint (uvicorn)
│   └── api/
│       ├── auth.py             # Login / register / JWT
│       ├── student.py          # /api/student/* routes
│       ├── recruiter.py        # /api/recruiter/* routes
│       └── deps.py             # Shared dependencies
│
├── frontend/                   # React + Vite
│   ├── src/
│   │   ├── App.jsx             # Router + sidebar
│   │   ├── api.js              # API client
│   │   ├── index.css           # Design system
│   │   ├── main.jsx            # Entry
│   │   └── pages/
│   │       ├── HomePage.jsx          # Landing dashboard
│   │       ├── StudentDashboard.jsx  # CV upload, search, results, applications
│   │       ├── RecruiterDashboard.jsx
│   │       └── LoginPage.jsx
│   └── package.json
│
├── config/
│   └── settings.py             # Environment config
├── models/
│   ├── user.py                 # User model
│   └── schemas.py              # Pydantic schemas
├── services/
│   └── auth_service.py         # Authentication logic
├── utils/
│   └── logger.py               # Logging setup
├── data/
│   ├── recrutia.db          # SQLite database for users and offers
│   └── *.json                  # Legacy/local data exports
├── scripts/
│   ├── push_to_github.sh
│   └── push_to_github.bat
│
├── .env                        # API keys (MISTRAL_API_KEY, etc.)
├── .gitignore
├── requirements.txt
└── README.md
```

## Running the Project

```bash
# Backend (from root)
uvicorn backend.main:app --reload --port 8000

# Frontend (from frontend/)
cd frontend && npm run dev
```

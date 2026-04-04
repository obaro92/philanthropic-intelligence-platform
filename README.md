# Access Digital Health — Philanthropic Intelligence Platform

AI-powered platform helping donors, funders, and portfolio managers make evidence-grounded giving decisions for global health and development.

**Three modes:**
- 🎯 **Donor Advisory** — Guided giving, impact calculator, and conversational AI advisor
- 📋 **Proposal Evaluator** — Upload grant proposals for evidence-based evaluation
- 📊 **Portfolio Assistant** — Daily intelligence for managing grant portfolios

## Quick Start (Local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Enter your Anthropic API key in the sidebar to start. The app works without a database (session-only storage) but data won't persist across refreshes.

## Deploy to Streamlit Cloud (Free)

### Step 1: Create accounts (all free)

1. **GitHub** — [github.com](https://github.com) (if you don't have one)
2. **Streamlit Cloud** — [share.streamlit.io](https://share.streamlit.io) (sign in with GitHub)
3. **Supabase** — [supabase.com](https://supabase.com) (sign in with GitHub)

### Step 2: Set up Supabase database

1. Create a new Supabase project (choose any region, free tier)
2. Wait for the project to initialize (~2 minutes)
3. Go to **SQL Editor** in the Supabase dashboard
4. Copy the contents of `sql/schema.sql` and run it
5. Go to **Settings → API** and copy:
   - **Project URL** (looks like `https://abcdefg.supabase.co`)
   - **service_role key** (the secret key, NOT the anon key)

### Step 3: Push to GitHub

```bash
# Create a new repository on GitHub, then:
git init
git add app.py db.py requirements.txt .streamlit/config.toml .gitignore README.md sql/
git commit -m "Initial commit — Philanthropic Intelligence Platform"
git remote add origin https://github.com/YOUR_USERNAME/giving-advisor.git
git push -u origin main
```

**Important:** Do NOT commit `.streamlit/secrets.toml` — it contains your API keys.

### Step 4: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Select your GitHub repository
4. Set **Main file path** to `app.py`
5. Click **Advanced settings** → **Secrets**
6. Paste your secrets:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

7. Click **Deploy**

Your app will be live at `https://your-app-name.streamlit.app` within 2-3 minutes.

## Architecture

```
app.py          — Main application (2,686 lines, 3 modes)
db.py           — Database integration layer (Supabase + in-memory fallback)
requirements.txt — Python dependencies
sql/schema.sql  — Database schema (run in Supabase SQL Editor)
.streamlit/
  config.toml   — Streamlit theme and settings
  secrets.toml  — API keys (DO NOT COMMIT)
```

### Data Persistence

| Data | Without DB | With Supabase |
|------|-----------|--------------|
| Chat history | Lost on refresh | Persists across sessions |
| Portfolio grants | Lost on refresh | Permanent storage |
| Evaluations | Lost on refresh | Searchable archive |
| Report analyses | Lost on refresh | Linked to grants |
| DHIS2 data | Queries every time | Cached for 24 hours |
| Donor profile | Lost on refresh | Remembered on return |
| Board reports | Lost on refresh | Quarter-over-quarter history |

### Data Sources

- 🏥 **DHIS2** — Health program data from national systems (129 countries)
- 📚 **Evidence base** — 30 interventions from GiveWell, DCP3, Cochrane, J-PAL
- 💰 **Cost-effectiveness** — Cost per DALY, cost per life saved, benefit-cost ratios
- 🏢 **Organizations** — 16 categories covering all GH&D sectors
- 🌐 **Web research** — Live current information via Claude's web capabilities

### API Requirements

- **Anthropic API** — Tier 2 recommended ($40 deposit, 450K tokens/minute)
- **Supabase** — Free tier (500MB storage, 50K monthly users)

## Built by

**Access Digital Health** — Lagos, Nigeria
Agentic AI for global health and development

Built for the Gates Foundation Grand Challenges: AI to Accelerate Charitable Giving

# Why this tech stack (viva notes)

| Choice | Why | Rejected alternative |
|---|---|---|
| **Python** | The core of ReliefGrid is the allocation algorithm (`app/allocation_engine.py`). Python is the natural language for algorithms, and the web layer shares it, so there is no integration gap. | Node/Express: would split the app and the algorithm across two languages. |
| **Flask** | Micro-framework: routing, sessions and templating without a forced structure, so the architecture (blueprints, services, pure engine) is our own design. | Django: its admin, ORM and conventions do much of the work and are heavy for a project whose novelty is the algorithm. |
| **SQLite + SQLAlchemy** | Data is relational (disaster -> locations -> requests -> deliveries; stock -> depots). Foreign keys and transactions help prevent over-allocation. SQLite needs zero setup and is one file. The ORM means PostgreSQL is a config change: set `DATABASE_URL`. | MongoDB: structured, relational data and integrity rules fit SQL better. |
| **Jinja2 server-rendered HTML + CSS** | Authentication and role-based views are enforced in one place (the server). Jinja2 auto-escapes output (XSS protection). | React: needs a build system and API layer; a conscious scope decision, not a skill gap. |
| **Vanilla JavaScript** (`static/app.js`) | Enough for slider read-outs, confirm dialogs, double-submit protection and friendly validation. Shows the fundamentals frameworks build on. All rules are also enforced server-side. | Frameworks: unnecessary for this UI. |
| **Chart.js** | Lightweight, open source, no build step. Bar charts for stock vs unmet demand, requested vs allocated, and current vs scenario plans. | D3: more code for the same charts. |
| **Flask-Login** | Standard, tested session management; no home-made login logic. | Writing our own sessions. |
| **Werkzeug password hashing** | Passwords stored only as salted hashes. | Plain text / MD5. |
| **Flask-WTF (CSRFProtect)** | CSRF tokens on every POST form. Validation of numbers and ranges is done server-side in the routes (`utils.intval`). | No CSRF protection. |
| **pytest** | Proves the algorithm: never allocates more than stock or more than requested, ranking order, empty input; plus RBAC and the full request -> allocation -> delivery workflow. | Manual testing only. |
| **Git / GitHub** | Version history, evidence of incremental development. | Zip files. |

## Algorithm: custom weighted priority score, not an optimizer (e.g. OR-Tools)
- **Explainable**: Module 5 requires saying *why* an allocation was recommended; every row stores a plain-language explanation.
- **Transparent**: officials can read and trust the formula: 100 x (0.40 urgency/5 + 0.25 population/max + 0.15 area severity/5 + 0.20 quantity/max).
- **Testable and understood**: pure Python, no Flask or DB, so it is unit-tested and reused by the simulation.
- **Future work**: a linear-programming optimizer or vehicle-capacity routing could be added as another mode.
- Two modes: priority-first (fill in rank order) and proportional sharing (score x quantity).

## Likely questions
- **Why Flask over Django?** Lightweight, full control, focus is the algorithm.
- **Why SQLite, will it scale?** Right for a prototype; set `DATABASE_URL` to PostgreSQL, no code change.
- **Why no React?** Scope control; server rendering is simpler and keeps access control in one place.
- **Why a custom algorithm?** Explainability and transparency.
- **How is security handled?** Hashed passwords, role-based access (admin/center guards return 403), CSRF tokens, server-side input validation, Jinja2 auto-escaping, POST-only logout, stock reservation to prevent over-allocation.
- **Weak points to admit honestly:** no vehicle capacities; SQLite is single-writer; default `SECRET_KEY` must be set via environment in production.

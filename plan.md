# TranslatorApp — Improvement Plan

> Living document tracking implemented improvements and future roadmap.
> Updated: 2026-02-19

---

## ✅ Completed

### Phase 0 — Subtitle Bug Fix & SSE (commit c5f7ee6)
- Fixed subtitle merging: SRT format end-to-end with per-cue translation
- Added SSE streaming progress bar for translation status
- Fixed admin auto-translate to use SSE flow

### Phase 1 — Security Hardening (commit 1b94dfa)
- **SQL injection**: Parameterized ~20 queries in 5 web-facing modules
  (user.py, contributions.py, glossary.py, kaContent.py, YoutubeDescriptionGenerator.py)
- **XSS**: Removed `|safe` from user data in templates, added `markupsafe.escape` for API data
- **Secret key**: Added `app.secret_key` from Configuration (was hardcoded "MySecretKey1")
- **Config template**: Rewrote Configuration.example.py with all keys documented
- **Field whitelist**: kaContent.saveData() now validates column names
- **Column whitelist**: YoutubeDescriptionGenerator.getKAData() validates KA types

### Phase 1.5 — Deployment Validation (current)
- Added `/health` endpoint (DB check, git version, no auth required)
- Fixed hardcoded secret in flaskapp.wsgi (now uses Configuration.secret_key via __init__.py)
- Created smoke test suite (pytest, 15 tests across all GET routes)
- Created validate.ps1 (Windows) and validate.sh (Linux) one-command validation
- Added requirements-dev.txt for test dependencies

---

## 🔲 Roadmap

### Phase 2 — Bugs & Code Cleanup
**Priority: High | Effort: Medium**

- [ ] Fix `statistic.py` SQL injection (focusCourseCondition uses f-strings)
- [ ] Fix `crowdin_pretranslate.py` SQL injection (same pattern)
- [ ] Fix outer `DBModule.py` — opens DB connection at import time
- [ ] Remove vestigial `app.py` at repo root (Hello Python scaffold)
- [ ] Pin dependency versions in requirements.txt
- [ ] Add proper error handling for missing Configuration values on startup
- [ ] Add request timeouts to all external API calls (DeepL, Amara, Crowdin, YouTube)
- [ ] Fix `kaContent.py` focusCourseCondition() — use parameterized queries for course list

### Phase 3 — Testing Expansion
**Priority: High | Effort: Medium**

- [ ] Set up a test MySQL database (`kadeutsch_test`) with schema migration script
- [ ] Add unit tests for `User` class (mock DB, test role parsing, cookie handling)
- [ ] Add unit tests for `SubtitleInfo.translateSubtitlesToSRT()` (mock DeepL)
- [ ] Add unit tests for `kaContent.saveData()` field whitelist validation
- [ ] Add unit tests for `YoutubeDescriptionGenerator` null-safe access
- [ ] Add integration tests using Flask test client (`app.test_client()`)
- [ ] Add test for 403 responses on permission failures (glossary, kaContent)
- [ ] Target: 60%+ coverage on web-facing modules

### Phase 4 — CI/CD with GitHub Actions
**Priority: Medium | Effort: Low-Medium**

- [ ] Create `.github/workflows/test.yml`:
  - Trigger on push to master and pull requests
  - Set up Python, install requirements-dev.txt
  - Run `pytest tests/` (smoke tests against Flask test client)
  - Lint with flake8 or ruff (catch syntax errors, unused imports)
- [ ] Create `.github/workflows/deploy.yml` (optional):
  - Trigger on push to master (after tests pass)
  - SSH to prod server, `git pull`, `sudo systemctl restart apache2`
  - Run `validate.sh https://kadeutsch.org` as post-deploy verification
- [ ] Add branch protection — require CI pass before merge

### Phase 5 — Code Consolidation
**Priority: Medium | Effort: Medium**

- [ ] Consolidate duplicate `DBModule.py` (outer vs inner `TranslatorApp/DBModule.py`)
- [ ] Create a shared `db.py` module with connection factory and context manager
- [ ] Extract common patterns: API client wrappers for DeepL, Amara, Crowdin
- [ ] Add type hints to function signatures
- [ ] Standardize error response format (all modules return JSON with error key)
- [ ] Move hardcoded strings (API URLs, table names) to Configuration

### Phase 6 — Security Hardening (Advanced)
**Priority: Medium | Effort: High**

- [ ] Add CSRF protection (Flask-WTF or custom token)
- [ ] Validate/HMAC WordPress auth cookies (currently trusting cookie content)
- [ ] Restrict CORS origins in subtitle.py (currently `*`)
- [ ] Add rate limiting on API endpoints
- [ ] Parameterize remaining CLI scripts (AmaraUpdate.py, YoutubeUpdate.py, etc.)
- [ ] Add Content-Security-Policy headers
- [ ] Audit and remove Configuration.py from git history (contains real API keys)

### Phase 7 — Documentation & Onboarding
**Priority: Low | Effort: Low**

- [ ] Update README.md with:
  - Local development setup instructions
  - How to run tests
  - How to deploy to production
  - Architecture overview (Flask blueprints, DB schema, external APIs)
- [ ] Add inline docstrings to remaining undocumented functions
- [ ] Document the WordPress authentication flow
- [ ] Create a CONTRIBUTING.md

---

## Deployment Checklist

### After every code change, run on DEV:
```powershell
.\validate.ps1
```

### After deploying to PROD:
```bash
ssh kadeutsch.org
cd /var/www/vhosts/kadeutsch.org/TranslatorApp/TranslatorApp
git pull origin master
sudo systemctl restart apache2
./validate.sh https://kadeutsch.org
```

### Quick manual health check:
```bash
curl https://kadeutsch.org/health
# Expected: {"db":"ok","status":"ok","version":"<hash>"}
```

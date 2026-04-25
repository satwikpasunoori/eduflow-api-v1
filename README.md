# EduFlow API

> AI-powered Course Platform REST API built with Flask — production-grade, fully documented, Swagger UI included.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![JWT](https://img.shields.io/badge/JWT-Auth-orange?style=flat-square)
![Swagger](https://img.shields.io/badge/Swagger-Docs-green?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)
![Gemini](https://img.shields.io/badge/Gemini-AI-purple?style=flat-square)

---

## Features

| Feature | Details |
|---------|---------|
| JWT Auth | Register, login, refresh tokens, role-based access |
| Roles | Admin / Instructor / Student — different permissions per role |
| Courses | Full CRUD — courses → modules → lessons (nested) |
| AI Summaries | Gemini API generates course descriptions + learning outcomes |
| Search & Filter | Search by title, filter by category/level/price, sort, paginate |
| Enrollment | Enroll in courses, mark lessons complete, track % progress |
| Analytics | Dashboard, popular courses, personal stats, instructor stats |
| Swagger Docs | Interactive API explorer at `/api/docs` — no Postman needed |
| Rate Limiting | Built-in per-endpoint rate limiting |
| Seed Data | 3 users + 3 courses loaded automatically on first run |

---

## Quick Start

### Docker (zero setup)

```bash
git clone https://github.com/satwikpasunoori/eduflow-api.git
cd eduflow-api
docker-compose up --build
```

Open **http://localhost:5000/api/docs** — Swagger UI loads instantly.

### Without Docker

```bash
git clone https://github.com/satwikpasunoori/eduflow-api.git
cd eduflow-api

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # edit if needed

python wsgi.py
```

Open **http://localhost:5000/api/docs**

---

## Gemini AI Setup (Optional)

The AI summary endpoint works **without** a Gemini API key — it returns a smart template response.

To enable real AI summaries:
1. Get a free API key at [aistudio.google.com](https://aistudio.google.com)
2. Add to `.env`: `GEMINI_API_KEY=your_key_here`
3. Restart the server
4. Call `POST /api/courses/{id}/ai-summary`

---

## Default Credentials (seeded on first run)

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@eduflow.com | admin123 |
| Instructor | satwik@eduflow.com | satwik123 |
| Student | student@eduflow.com | student123 |

---

## API Reference

### Auth
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Get JWT tokens |
| POST | `/api/auth/refresh` | Refresh token | Get new access token |
| GET | `/api/auth/me` | Yes | My profile |
| PUT | `/api/auth/me` | Yes | Update profile |

### Courses
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/courses` | No | List courses (search, filter, paginate) |
| POST | `/api/courses` | Instructor/Admin | Create course |
| GET | `/api/courses/{id}` | No | Course detail with modules+lessons |
| PUT | `/api/courses/{id}` | Owner/Admin | Update course |
| DELETE | `/api/courses/{id}` | Owner/Admin | Delete course |
| POST | `/api/courses/{id}/ai-summary` | Owner/Admin | Generate AI summary |
| GET | `/api/courses/{id}/modules` | No | List modules |
| POST | `/api/courses/{id}/modules` | Instructor/Admin | Add module |
| POST | `/api/courses/modules/{id}/lessons` | Instructor/Admin | Add lesson |
| POST | `/api/courses/{id}/enroll` | Student | Enroll in course |
| GET | `/api/courses/{id}/progress` | Student | My progress |
| POST | `/api/courses/lessons/{id}/complete` | Student | Mark lesson done |

### Analytics
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/analytics/dashboard` | Admin | Full platform stats |
| GET | `/api/analytics/popular-courses` | No | Top 10 courses |
| GET | `/api/analytics/my-stats` | Student | Personal learning stats |
| GET | `/api/analytics/instructor-stats` | Instructor | My courses performance |

### Users
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/users/my-courses` | Student | All my enrollments |
| GET | `/api/users/all` | Admin | All users |

---

## Project Structure

```
eduflow-api/
├── wsgi.py                  # Entry point
├── config.py                # All configuration
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── app/
    ├── __init__.py          # App factory + seed data
    ├── extensions.py        # db, jwt, bcrypt, limiter
    ├── models/
    │   └── __init__.py      # User, Course, Module, Lesson, Enrollment, LessonProgress
    ├── routes/
    │   ├── auth.py          # Auth endpoints
    │   ├── courses.py       # Course + enrollment endpoints
    │   ├── analytics.py     # Analytics endpoints
    │   └── users.py         # User endpoints
    └── utils/
        └── __init__.py      # AI helper, role decorator, pagination
```

---

## Example Requests

**Register & Login**
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Satwik","email":"me@example.com","password":"pass123","role":"instructor"}'

curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"pass123"}'
```

**Search Courses**
```bash
curl "http://localhost:5000/api/courses?q=python&level=beginner&sort=rating"
```

**Generate AI Summary**
```bash
curl -X POST http://localhost:5000/api/courses/1/ai-summary \
  -H "Authorization: Bearer <your_token>"
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Flask 3.0 + Flask-RESTX |
| Database | SQLite + SQLAlchemy ORM |
| Auth | Flask-JWT-Extended |
| Password | Flask-Bcrypt |
| Rate Limiting | Flask-Limiter |
| API Docs | Swagger UI (auto-generated) |
| AI | Google Gemini API |
| Server | Gunicorn |
| Container | Docker + Docker Compose |

---

## Deploy to Render

1. Push to GitHub
2. Go to render.com → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
5. Add env vars: `SECRET_KEY`, `JWT_SECRET_KEY`, optionally `GEMINI_API_KEY`

---

## Author

**Satwik Pasunoori**
- GitHub: [@satwikpasunoori](https://github.com/satwikpasunoori)
- Email: satwikpasunoori@gmail.com

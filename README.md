# SRIT — Dockerized College Portal

A polished college portal built with **Flask + SQLite + HTML/CSS/JS + Docker**.

## Features
- Student registration with mandatory identity/academic fields
- Student directory showing registered students, Registration IDs, department, year/section and CGPA
- Individual student profile
- Staff-only Marks Center
- Subject marks → automatic grade → credit-weighted CGPA
- Update marks for an existing subject
- Search and department filtering
- Persistent SQLite database using Docker volume
- Gunicorn production server inside the container
- Responsive premium UI

## Run in VS Code

### Option A — Docker (recommended)
Install Docker Desktop, open this folder in VS Code terminal, then:

```bash
docker compose up --build
```

Open:
http://localhost:5000

Stop:
```bash
docker compose down
```

The database persists in the `college_data` Docker volume.

### Option B — Run locally
```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Then:
```bash
pip install -r requirements.txt
python app.py
```

## Staff demo account
Username: `admin`
Password: `admin123`

## Workflow
1. Open Register Student.
2. Register 10 students or any number of students.
3. Open Staff Login.
4. Dashboard displays the complete student list.
5. Open Marks Center.
6. Select a student and enter subject code, subject, credits and marks.
7. The system maps marks to grade points:
   - 90–100 = O = 10
   - 80–89 = A+ = 9
   - 70–79 = A = 8
   - 60–69 = B+ = 7
   - 50–59 = B = 6
   - 40–49 = C = 5
   - Below 40 = F = 0
8. CGPA = Σ(credit × grade point) / Σ(credits).

## DevOps upgrade path
For a college deployment, add:
- PostgreSQL instead of SQLite
- Redis for caching
- Nginx reverse proxy
- HTTPS/TLS
- Docker secrets / environment variables
- GitHub Actions CI/CD
- Automated tests
- Role-based permissions for multiple staff accounts
- Audit logs
- Backup and restore
- Cloud deployment (AWS/Azure/GCP)

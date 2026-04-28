# Module 14 IS 601 - FastAPI Calculations App

## Project Overview

This projetct is FastAPI-based calculations application with user authentication, full BREAD functionality for calculations, and an additional profile management feature. Users can register, log in, create and manage calculations, and update their own profile information. The project also includes automated testing, containerized deployment with Docker, and CI/CD through GitHub Actions.

### Authentication
- User registration
- User login with JWT-based authentication
- Protected routes for authenticated users
- Password hashing using bcrypt

### Calculation Management (BREAD)
- **Browse** all saved calculations for the logged-in user
- **Read** individual calculation details
- **Edit** existing calculations
- **Add** new calculations
- **Delete** calculations

### Additional Feature
- **Profile Management**
  - View current user profile with `GET /users/me`
  - Update first name, last name, and email with `PUT /users/me`

## Tech Stack

- **Backend:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Authentication:** JWT
- **Testing:** Pytest
- **E2E Testing:** Playwright / Requests-based E2E tests
- **Containerization:** Docker / Docker Compose
- **CI/CD:** GitHub Actions
- **Security Scanning:** Trivy
- **Admin Tool:** pgAdmin

## Project Structure

```text
app/
  auth/
  core/
  models/
  schemas/
  main.py
templates/
tests/
  unit/
  integration/
  e2e/
docker-compose.yml
Dockerfile
requirements.txt
README.md

To run prject locally:
1. Clone the repository:
git clone git@github.com:danielleev33/module14_is601.git
cd module14_is601

2. Start the application:
docker compose up --build -d

3. Open the app:
App: http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs
pgAdmin: http://127.0.0.1:5050

Web Routes
/ - landing page
/register - user registration page
/login - login page
/dashboard - main calculations dashboard
/dashboard/view/{calc_id} - view a specific calculation
/dashboard/edit/{calc_id} - edit a specific calculation

API Routes
Auth
POST /auth/register
POST /auth/login
POST /auth/token

Calculations
GET /calculations
POST /calculations
GET /calculations/{calc_id}
PUT /calculations/{calc_id}
DELETE /calculations/{calc_id}

User Profile
GET /users/me
PUT /users/me

Running Tests
Run the full test suite:
docker compose exec web pytest -v

Run tests without coverage plugin issues:
docker compose exec web pytest -p no:cov -o addopts='' -v

Run unit tests only:
docker compose exec web pytest -p no:cov -o addopts='' tests/unit -v

Run integration tests only:
docker compose exec web pytest -p no:cov -o addopts='' tests/integration -v

Run E2E tests only:
docker compose exec web pytest -p no:cov -o addopts='' tests/e2e/test_fastapi_calculator.py -v

Docker Hub Image:
danielleev33/module14_is601

During development I made some updates to get everything fully working:
- updated dependencies flagged by Trivy
- replaced python-jose w/ PyJWT for cleaner JWT handling
- fixed Swagger auth to use correct token endpoint
- made Redis blacklist checks fail safely when Redis is unavailable for testing
- added the profile management feature as required feature
- verified calculation BREAD functionality through testing

Screenshots Included:
calculation dashboard w/ BREAD functionality
calculation details/ read page
profile feature working through successful PUT /users/me update
successful GitHub Actions pipeline
Docker Hub image deployment
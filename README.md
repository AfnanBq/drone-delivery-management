# Drone Delivery Management APIs

## Overview

Drone Delivery Management APIs is a Python FastAPI backend for managing drone delivery operations. It supports user role management, authenticated access, drone location tracking, order creation, and spatial order assignment using PostgreSQL/PostGIS.

### What this project does

- Manages users in roles: `admin`, `enduser`, and `drone`
- Creates delivery orders with origin and destination geographic coordinates
- Finds nearest available drones for orders using PostGIS spatial queries
- Supports drone status, location updates, handoff workflows, and order lifecycle transitions
- Uses JWT authentication for secure API calls

### Main use cases

- Admins can manage users and inspect all drones and orders
- End users can submit orders and withdraw orders before pickup
- Drones can reserve available orders, report location changes, and update order status

### Key features

- FastAPI REST API with `/api/v1` versioned routing
- JWT bearer authentication and role-based authorization
- PostGIS-enabled spatial matching for drones and orders
- SQLAlchemy ORM with Alembic migrations
- Docker Compose configuration for local development

## Architecture

The repository separates HTTP routing, business logic, and persistence.

- `app/main.py`: application startup, router inclusion, and health endpoint
- `app/api/api.py`: grouped API router for auth, user, drone, and order modules
- `app/api/endpoints/*`: request handlers for each resource
- `app/services/*`: business workflows and validation
- `app/crud/*`: database operations and PostGIS queries
- `app/models/*`: SQLAlchemy models for the domain
- `app/schemas/*`: Pydantic schemas for request validation and response serialization
- `app/core/*`: environment configuration, database session setup, and JWT utilities

### High-level data flow

```mermaid
flowchart LR
    Client -->|HTTP| FastAPI
    FastAPI --> Router
    Router --> Endpoint
    Endpoint --> Service
    Service --> CRUD
    CRUD --> PostgreSQL/PostGIS
```

### Important components

- `app/api/endpoints/auth.py`: creates JWT tokens for existing users
- `app/api/endpoints/user.py`: admin-only user list and create endpoints
- `app/api/endpoints/drone.py`: drone location updates, status changes, handoff, and assigned order retrieval
- `app/api/endpoints/order.py`: order creation, reservation, withdrawal, location updates, and status transitions
- `app/core/config.py`: loads environment variables and assembles the DB connection string
- `app/core/security.py`: creates JWT access tokens
- `app/services/*`: encapsulates domain logic and error handling
- `app/crud/*`: performs DB reads/writes and spatial queries

## Technology Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL with PostGIS
- GeoAlchemy2
- Alembic
- Pydantic / pydantic-settings
- Uvicorn
- pytest
- Docker / Docker Compose

## Installation

### Prerequisites

- Python 3.12
- Docker and Docker Compose (recommended)
- PostgreSQL with PostGIS if running without Docker

### Environment setup

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Edit `.env` to match your local database credentials and JWT secret.

3. When using Docker Compose, set `POSTGRES_SERVER=db` in `.env` so the API container can reach the database service.

### Install Python dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

The application loads configuration from `.env` via `app/core/config.py`.

### Required environment variables

- `POSTGRES_SERVER`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `SECRET_KEY`

### Optional values

- `DEBUG`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `SQLALCHEMY_DATABASE_URI`

> Note: `POSTGRES_PORT` is present in `.env.example` but is not currently consumed by `app/core/config.py`.

## Quick Start

### Run with Docker Compose

```bash
docker compose up --build
```

The API is available at:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

### Run locally without Docker

```bash
source .venv/bin/activate
cp .env.example .env
# update .env values for your local PostgreSQL/PostGIS server
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Summary

- `GET /health`
- `POST /api/v1/auth/token`
- `GET /api/v1/user/`
- `POST /api/v1/user/`
- `GET /api/v1/drone/`
- `PATCH /api/v1/drone/{drone_id}`
- `PATCH /api/v1/drone/me/location`
- `POST /api/v1/drone/me/request-handoff`
- `GET /api/v1/drone/me/order`
- `GET /api/v1/order/`
- `POST /api/v1/order/`
- `GET /api/v1/order/my-orders`
- `PATCH /api/v1/order/{order_id}/locations`
- `PATCH /api/v1/order/{order_id}/withdraw`
- `POST /api/v1/order/reserve`
- `PATCH /api/v1/order/{order_id}/event`

### Example requests

Health check:

```bash
curl http://localhost:8000/health
```

Authenticate an existing user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"name": "admin", "role": "admin"}'
```

Create a user (admin only):

```bash
curl -X POST http://localhost:8000/api/v1/user/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "new_user", "role": "enduser"}'
```

Submit an order (enduser):

```bash
curl -X POST http://localhost:8000/api/v1/order/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"origin_location": [39.0, 21.0], "destination_location": [39.1, 21.1]}'
```

Reserve an order (drone only):

```bash
curl -X POST http://localhost:8000/api/v1/order/reserve \
  -H "Authorization: Bearer <token>"
```

## Testing

Run tests with:

```bash
pytest app/tests
```

The tests depend on a reachable PostgreSQL database configured through `.env` and `app/core/config.py`.

## Development

### Local workflow

1. Create and activate a Python virtual environment
2. Install dependencies from `requirements.txt`
3. Configure `.env`
4. Run `alembic upgrade head`
5. Start the app with `uvicorn app.main:app --reload`

### Generating new migrations

When you change models, create a new Alembic revision and apply it:

```bash
alembic revision --autogenerate -m "describe changes"
alembic upgrade head
```

Ensure your models are importable by Alembic; this repository already imports `app.models` in `alembic/env.py`.

### Formatting and linting

No formatter or linter is included in the repository. Recommended commands:

```bash
black .
flake8 .
isort .
```

## Troubleshooting

- **Compose cannot connect to Postgres**: set `POSTGRES_SERVER=db` in `.env` for Docker Compose
- **401 / 403 auth errors**: token creation requires an existing user with the matching role
- **No initial admin user**: create the admin user directly in the database before using admin-only endpoints
- **PostGIS function errors**: confirm the DB server has PostGIS enabled and the `postgis/postgis:16-3.4` image is used
- **Alembic migration failures**: ensure `.env` is loaded and DB credentials are correct

## Project Structure

- `app/`
  - `main.py` – FastAPI app entrypoint
  - `api/` – endpoint routing
  - `core/` – settings, DB, and security helpers
  - `models/` – SQLAlchemy ORM models
  - `crud/` – database access layer
  - `services/` – business logic and workflows
  - `schemas/` – Pydantic request/response definitions
  - `tests/` – pytest test modules and fixtures
- `alembic/` – migration scripts and config
- `Dockerfile` – container image build steps
- `docker-compose.yaml` – local PostGIS + API composition
- `.env.example` – environment variable template
- `requirements.txt` – Python dependencies

## Deployment

### Docker

Build and run the containerized stack:

```bash
docker compose up --build
```

The API will be reachable at `http://localhost:8000`.

### Migrations

Run Alembic migrations before using the API:

```bash
alembic upgrade head
```

## Troubleshooting

- `401 Unauthorized` or `403 Forbidden`: verify the JWT token and user role
- `Database connection errors`: confirm `.env` values and that PostgreSQL/PostGIS is running
- `PostGIS function errors`: ensure the database image is `postgis/postgis` or PostGIS is installed
- Missing admin user: the API expects a valid admin user to create other users, so create an initial admin user directly in the database if needed

## Contributing

Contributions are welcome. For best results:

- Open issues for bugs or feature requests
- Use `pytest app/tests` to validate changes
- Keep business logic in `app/services` and persistence in `app/crud`

## License

No license file is included in this repository. TODO: add a `LICENSE` file to clarify usage rights.

# By the Book

Inspection reports, security deposits, rent receipts, notices, and maintenance records for Alberta rental properties.

This is not legal advice. The statements follow section 4 of the Residential Tenancies Ministerial Regulation. Check the current Act and have an Alberta landlord-tenant lawyer review the template before you rely on it.

## Layout

`frontend/` is the website (Vite, React, TypeScript). `mobile/` is the React Native app (Expo). `backend/` is Django and Django REST framework. PostgreSQL when `DB_HOST` is set, SQLite otherwise.

The website signs in with a session cookie. The phone app uses the token returned by the same login and register endpoints.

## Run it on this machine

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

```powershell
cd frontend
npm install
npm run start
```

Open http://localhost:3000. The Vite dev server proxies `/api` to Django on port 8000. Reminder emails print in the Django console until SMTP is configured.

## Phone app

With the API running:

```powershell
cd mobile
npm install
npx expo start
```

Expo prints a QR code for the Expo Go app, plus options for an Android emulator, an iOS simulator, and a browser preview. The app calls `http://127.0.0.1:8000` unless `EXPO_PUBLIC_API_URL` is set. An Android emulator should use `http://10.0.2.2:8000`. A physical phone should use your computer’s LAN address, for example `http://192.168.1.20:8000`.

```powershell
cd backend
.\.venv\Scripts\python manage.py send_reminders
```

## Docker

Copy `.env.example` to `.env`, then:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

The dev stack is Postgres, Django on port 8000, and Vite on port 3000. `make dev` does the same thing when `make` is installed.

## Tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

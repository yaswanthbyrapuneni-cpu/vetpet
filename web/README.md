# Madina Vet Pet web client

Responsive React and TypeScript client for the Madina Vet Pet FastAPI backend.
It is the active frontend and can be installed as a Progressive Web App.

## Development

Start the backend on port 8000, then:

```powershell
cd web
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to
`http://127.0.0.1:8000`, so local development does not require CORS changes.

## Verification

```powershell
npm.cmd run lint
npm.cmd run test
npm.cmd run build
```

Set `VITE_API_URL` when deploying the frontend separately from the API. Production
must use HTTPS. Access tokens currently use browser local storage because the API
returns bearer tokens; a later security milestone should move web sessions to
Secure, HttpOnly, SameSite cookies.


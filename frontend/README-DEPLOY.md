# Wedding frontend deployment

This frontend is configured to call the deployed FastAPI backend at `https://bride-wedding.vercel.app/` by default. You can override it with `VITE_API_BASE_URL`.

## Vercel settings
- Root Directory: `frontend` (if deploying from the monorepo).
- Framework Preset: Vite.
- Build Command: `npm run build`.
- Output Directory: `dist`.
- Environment Variable: `VITE_API_BASE_URL=https://bride-wedding.vercel.app/` (Production and Preview as appropriate).
- Redeploy after adding/changing environment variables.

## Backend CORS
In the backend Vercel project, set `CORS_ORIGINS` to the exact deployed frontend origin, such as `https://your-frontend-domain.vercel.app`. Do not include a path. Multiple origins can be comma-separated. Redeploy backend after changes.

## Features
- Guest blessings submit to `POST /api/wishes`.
- Private `/admin` page logs in through `POST /api/admin/login` and reads/deletes blessings through admin endpoints.
- Admin requires `ADMIN_PASSWORD` and `TOKEN_SECRET` in backend Vercel environment variables.


## Bride-side deployment using the existing Neon project

For this bride-side frontend, set `VITE_API_BASE_URL` to the URL of the bride-side backend Vercel deployment. In that backend's Vercel Environment Variables, set `DATABASE_URL` to the same Neon connection string used by the groom-side backend, `WEDDING_ID=heena-bride-side`, and its own `ADMIN_PASSWORD` and `TOKEN_SECRET`. The groom-side records remain separate through `wedding_id`.

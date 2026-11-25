# Dashboard API

FastAPI service used by the dashboard's transaction table and metric cards.

## Start

Put `MONGO_URI` in `Api/.env`, then run from this folder:

```powershell
uv run fastapi dev dashboard_app.py
```

The frontend uses `http://localhost:8000/api` by default. Set `VITE_API_URL` in `Dashboard/.env` only when the API runs at a different URL. Interactive API docs are at `http://localhost:8000/docs`.

For deployment, set `VITE_API_URL` to the deployed API's `/api` URL and set `DASHBOARD_ORIGINS` to a comma-separated list of allowed frontend origins.

## Deploy the backend

The API includes a Dockerfile and a root-level `render.yaml` Blueprint for Render. The Blueprint uses Render's free web-service plan and sets port `10000` and `/health` as the health check. Render's free services can spin down while idle. See [Render's free instance details](https://render.com/docs/free).

To create the Render service, push this repository to a Git host, choose **New → Blueprint** in Render, and connect the repository. Render will ask for `MONGO_URI`; enter it in Render's environment prompt, not in this repository. Confirm MongoDB network access allows the deployed service to connect. The blueprint builds from `Api/Dockerfile`.

The service environment is configured with these values; do not put production secrets in source files:

- `MONGO_URI`: the MongoDB connection string, with network access enabled for the host.
- `DASHBOARD_ORIGINS`: currently local development origins. After frontend deployment, replace these with the exact frontend origin(s), comma-separated.
- `MONGO_DATABASE` and `MONGO_COLLECTION` are optional; they default to `Dashboard-DB` and `Transactions`.

After deploy, open `/health` on the service URL. It should return `database: connected`. To connect the local frontend, copy `Dashboard/.env.example` to `Dashboard/.env.local` and replace the example with the actual Render URL plus `/api`. Later, set the same `VITE_API_URL` in the frontend hosting settings and rebuild/redeploy the frontend. Vite reads it at build time.

The API stores dashboard records in the `Dashboard-DB.Transactions` collection by default. Override those names with `MONGO_DATABASE` and `MONGO_COLLECTION` if needed.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/transactions` | Search, filter, sort, and paginate transactions |
| `POST` | `/api/transactions` | Add a transaction |
| `GET` | `/api/transactions/{id}` | Read one transaction |
| `PATCH` | `/api/transactions/{id}` | Edit transaction fields |
| `DELETE` | `/api/transactions/{id}` | Delete one transaction |
| `DELETE` | `/api/transactions/bulk` | Delete `{ "ids": ["..."] }` |
| `GET` | `/api/dashboard/metrics?period=Daily&date=2026-11-18` | Period metrics and chart buckets |
| `GET` | `/api/dashboard/revenue-breakdown?start=2026-11-01&end=2026-11-18` | Revenue grouped by product for the chart date range |
| `GET` | `/health` | Service health |

Transaction create fields are `customer`, `product`, `status`, `quantity`, `unitPrice`, and optional ISO `date`. Status is `Success`, `Pending`, or `Refunded`. Revenue and product breakdowns count successful transactions. The conversion card reports successful transactions divided by all transactions because this dashboard does not yet collect website visits. Metrics compare with the immediately preceding period of the same length; the sales chart compares monthly revenue with the prior year.

# Frontend — CareFlow Nexus Operations Workbench

**The frontend is included in this repository** under [`frontend/`](../frontend/). It is a responsive **React 19 + Vite 6** application, served through Nginx when running the Docker Compose stack. This is the actual UI source, not just a backend/API project.

## Frontend views

| View | Purpose | Where it appears |
| --- | --- | --- |
| **Sign in** | Secure local credential entry and session handling | Initial screen |
| **Overview** | Case counts, pending reviews, proposed/approved tasks and recent case queue | Sidebar → Overview |
| **Case workbench** | Search cases, inspect findings, view evidence, investigate, approve/reject tasks | Sidebar → Case workbench |
| **Agent intelligence** | Describe the four bounded specialists and evidence-validation model | Sidebar → Agent intelligence |
| **Governance** | Explain approval, provenance, authorization, audit and clinical-safety boundaries | Sidebar → Governance |

Inside a case, use the **Findings**, **Source evidence**, **Agent trace** and **Audit log** tabs. Approval buttons are shown only to users with authorized roles. This is a synthetic demonstration environment, not a live EHR.

## Frontend source

- [`src/App.jsx`](src/App.jsx) — components, routing/panels, API calls, case actions and approvals
- [`src/style.css`](src/style.css) — responsive styling and layouts
- [`src/main.jsx`](src/main.jsx) — React app entrypoint
- [`vite.config.js`](vite.config.js) — local development proxy to the API
- [`nginx.conf`](nginx.conf) — frontend/API reverse proxy in the container deployment
- [`Dockerfile`](Dockerfile) — frontend image build

## Run the full frontend + backend

From the repository root, configure `.env` from `.env.example`, then:

```bash
docker compose up --build -d
```

Open **http://localhost:8088**. Sign in with the `ADMIN_USERNAME` and `ADMIN_PASSWORD` configured in your local `.env`. There are no publicly published default credentials.

## Run the frontend in development mode

First run the backend on port 8000 as described in the [root README](../README.md#developer-mode-without-docker). Then:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The dev server proxies `/api` requests to the backend.

```bash
npm run build
```

Builds the production UI. **The frontend is not separately deployed to a public URL.** Seeing the source on GitHub or seeing a passing frontend CI build does not mean a hosted demo is available.

> **Screenshot status:** The repository currently includes UI source but no checked-in verified application screenshots. Do not confuse an architecture drawing or mockup with a screenshot of the running application.

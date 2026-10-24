# Preview deployment

The preview runs on Azure for Students, Neon and GitHub Actions: a static website for `web/`, a scale-to-zero container for `api/`, a managed PostgreSQL, and a scheduled workflow that ingests every source into it every 6 hours.

- Site: <https://hoshizorapreview.z48.web.core.windows.net/en> (and `/ja`)
- API: <https://hoshizora-api.lemonrock-d6e24592.malaysiawest.azurecontainerapps.io/actuator/health>

## Layout

| Piece | Host | Settings |
|---|---|---|
| Web | Azure Storage static website, `hoshizorapreview` (Standard LRS) | `index.html` as index and error document, hashed assets `immutable`, `index.html` `no-cache` |
| API | Azure Container Apps (express environment `hoshizora`, app `hoshizora-api`) | 0.5 vCPU, 1 GiB, 0 to 1 replicas, logs destination `none`, `CORS_ALLOWED_ORIGINS` set to the site's origin |
| Image | GitHub Container Registry, public | `ghcr.io/froxily/hoshizora-api:<commit>` and `:latest`, built by `.github/workflows/api-image.yml` |
| PostgreSQL | Neon, AWS Asia Pacific (Singapore) | Free plan: 1 GB storage and 100 CU-hours a month per project, suspends after 5 minutes idle; the preview database is about 104 MB. Cap the compute at 0.25 CU (see below) |
| Ingestion | GitHub Actions, `.github/workflows/ingest.yml` | `hoshizora ingest-all --max-wait 120` at 00:17, 06:17, 12:17 and 18:17 UTC, 20 minute timeout, repository secret |
| Budget | Azure Cost Management, `hoshizora-preview` | 5 USD a month; emails the subscription owners at 50 % and 100 % of actual cost and 100 % of forecast |

Everything lives in the resource group `hoshizora-preview` in **Malaysia West**. The Azure for Students subscription only allows UAE North, Malaysia West, Central India, Korea Central and Indonesia Central, and Malaysia West is the closest to Neon's Singapore.

### Decisions

- **No Static Web Apps.** It only exists in Central US, East US 2, West US 2, West Europe and East Asia, none of which the subscription allows, so the site is a Storage static website. It cannot rewrite paths or set the `nosniff` and `Referrer-Policy` headers.
- **Deep links are route shells.** The storage website serves a blob whose name equals the path. After the build, `web/scripts/route-shells.ts` writes a copy of `index.html` for home, every page and every agency profile in both languages, each with its own `lang`, title, description, canonical link, `hreflang` alternates and Open Graph tags. `just preview-web` uploads them as extensionless `text/html` blobs (`ja/sun`, `en/agencies/jaxa`), one batch per path depth, since `en/agencies` and `en/agencies/jaxa` cannot both be files on disk. Known paths answer 200; anything else still gets the 404 document. The app removes the shell tags at startup and renders its own.
- **Ingestion runs on GitHub Actions, not Azure.** A Container Apps job would need an ingest image, an Azure identity and secrets in two places. The workflow needs one secret. It runs every 6 hours, a few minutes a day; hourly also fits within free Actions minutes for a public repository ([ADR 0009](decisions/0009-scheduled-ingestion-and-raw-retention.md)).
- **The browser calls the API directly.** A static website cannot proxy `/api`, so the web build bakes the API URL in (`VITE_API_BASE_URL`), and the API answers CORS itself for the origins in `hoshizora.cors.allowed-origins` (`CORS_ALLOWED_ORIGINS`): reads only, exposing `ETag` and `Content-Language`.
- **CORS lives in the API, not the ingress.** The Container Apps ingress CORS policy replaces the API's `Vary: Accept-Language` with `Vary: Origin` on cross-origin responses, so browsers served an English response on Japanese pages from their cache. Spring's CORS handling adds `Origin` to `Vary` and keeps `Accept-Language`.
- **Public image, no registry secret.** The image holds only the compiled API, no secrets or data, so pulling it needs no token.
- **Express environment.** `az containerapp env create` made one. It supports everything the API needs (scale to zero, secrets, CORS, HTTP probes) and starts replicas quickly. `az containerapp logs show` does not work on it.

### Where each secret lives

| Secret | Lives in | Entered by |
|---|---|---|
| Neon connection string, role passwords | The terminal session that runs the `preview-*` recipes | The maintainer, at a hidden prompt |
| `hoshizora_api` password | Container App secret `db-password` | `just preview-secrets`, from that session or a hidden prompt |
| JDBC URL (no password) | Container App secret `db-url` | CLI |
| `hoshizora_ingest` connection URL | GitHub repository secret `PREVIEW_INGEST_DATABASE_URL` (moves to a main-only environment `preview` once the repository is public) | `just preview-ingest-setup` (or `just preview-ingest-secret`), from hidden prompts |

Nothing secret goes in git, `.env`, workflow logs or chat.

## Steps

### 1. Neon: create the database

1. Create a project named `hoshizora` with **PostgreSQL 18** in **AWS Asia Pacific (Singapore)**.
2. In **Connect**, turn **Connection pooling** off (the direct connection) and copy the connection string. Keep it out of files: the next step reads it into the terminal.

### 2. Local: migrate and load the preview database

The secrets live only in the terminal session. In PowerShell:

```
$env:PREVIEW_DATABASE_URL = [Net.NetworkCredential]::new('', (Read-Host 'Neon connection string' -AsSecureString)).Password
$env:PREVIEW_API_DB_PASSWORD, $env:PREVIEW_INGEST_DB_PASSWORD = 1..2 | ForEach-Object { $b = [byte[]]::new(24); [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); -join ($b | ForEach-Object { $_.ToString('x2') }) }
```

In bash or zsh: `read -rs PREVIEW_DATABASE_URL && export PREVIEW_DATABASE_URL`, and `export PREVIEW_API_DB_PASSWORD=$(openssl rand -hex 24) PREVIEW_INGEST_DB_PASSWORD=$(openssl rand -hex 24)`.

Then, in the same terminal:

```
just up
just preview-migrate   # Flyway: schemas, tables, marts and the two login roles
just preview-load      # copies raw, core and facts from your local database in one transaction, then refreshes every mart
```

`preview-load` refuses to run against a database that already has data. `pg_dump --data-only` does not carry materialized view contents, so the load ends by refreshing each mart in the order ingest uses; `just preview-refresh` does only that step. Keep the terminal open for step 4.

### 3. Azure: resources

Sign in with `az login` and pick the Azure for Students subscription. Check the allowed regions with `az policy assignment list`, then:

```
az provider register -n Microsoft.App --wait
az provider register -n Microsoft.Storage --wait
az group create -n hoshizora-preview -l malaysiawest
az containerapp env create -n hoshizora -g hoshizora-preview -l malaysiawest --logs-destination none
az containerapp create -n hoshizora-api -g hoshizora-preview --environment hoshizora --image ghcr.io/froxily/hoshizora-api:latest --ingress external --target-port 8080 --cpu 0.5 --memory 1.0Gi --min-replicas 0 --max-replicas 1
az storage account create -n hoshizorapreview -g hoshizora-preview -l malaysiawest --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false --https-only true
az storage blob service-properties update --account-name hoshizorapreview --auth-mode key --static-website --index-document index.html --404-document index.html
```

The budget is a `PUT` with `az rest` to `/subscriptions/<id>/providers/Microsoft.Consumption/budgets/hoshizora-preview` (API version 2023-05-01), notifying the `Owner` role.

### 4. Secrets and wiring

In the terminal from step 2:

```
just preview-secrets
```

Then:

```
az containerapp secret set -n hoshizora-api -g hoshizora-preview --secrets "db-url=jdbc:postgresql://<neon host>/neondb?sslmode=require"
az containerapp update -n hoshizora-api -g hoshizora-preview --set-env-vars DATABASE_URL=secretref:db-url DATABASE_USER=hoshizora_api DATABASE_PASSWORD=secretref:db-password CORS_ALLOWED_ORIGINS=https://hoshizorapreview.z48.web.core.windows.net
just preview-web
```

### 5. Scheduled ingestion

The ingest URL is a repository secret. In a public repository it can move to a main-only environment `preview` instead (see below).

In the Terminal panel tab where you are signed in to `az` and `gh`, run `just preview-ingest-setup`. It asks for the Neon connection string at a hidden prompt (the owner's direct connection, from step 1), then:

1. keeps the API's password stored in the Container App secret `db-password` (or generates one if there is none), gives `hoshizora_ingest` a new password, and runs `just preview-migrate`, which applies new migrations (V19) and sets both passwords;
2. logs in as each role once, and stops before touching Azure or GitHub if either login fails;
3. stores the API's password with `just preview-secrets`, only when it was newly generated;
4. restarts the API with `just preview-api-restart` (see below) and waits until a new replica answers `/actuator/health` with `UP` and `/api/v1/meta/sources` from the database;
5. stores `postgresql://hoshizora_ingest:…@<host>/neondb?sslmode=require` as the repository secret `PREVIEW_INGEST_DATABASE_URL` with `just preview-ingest-secret`, piped through standard input.

Run on its own, `just preview-ingest-secret` asks for the Neon connection string, gives `hoshizora_ingest` a fresh password (`ALTER ROLE` from a container, the password passed as a psql variable, never an argument), checks the login and stores the secret. Use it when only the GitHub secret is missing.

The recipe is safe to rerun after a failure at any step: the API's password never changes once stored, and the ingest password only lives in the GitHub secret, so it is simply replaced. Passwords exist only inside the run and in Azure and GitHub.

In Neon, open the project's **Branches → main → Computes → Edit** and set the compute size to a fixed **0.25 CU**. Each run wakes the database for a few minutes; at 0.25 CU that stays well inside the 100 CU-hours a month, while autoscaling up to 2 CU could use them up.

Merge the branch that adds `.github/workflows/ingest.yml`, then run it once from **Actions → Ingest → Run workflow**. Later runs start on their own at 00:17, 06:17, 12:17 and 18:17 UTC.

- **Going hourly.** Actions minutes are free in a public repository: change the cron to `17 * * * *` and move the secret to a main-only environment `preview` (`environment: preview` on the job). The aurora map and space-weather facts then refresh every hour instead of every six.
- **Migrations first.** Ingest has no DDL rights, so run `just preview-migrate` (or `just preview-ingest-setup` again) before merging a pull request that adds a migration. Otherwise the next scheduled run fails on the missing table or column.
- **Held for review.** A source whose last run ended `needs_review` (CelesTrak stops on any non-200, as its policy asks) is not requested again, and every run fails with exit code 3 until someone checks the cause. Then run the workflow once with **reviewed** ticked.
- **Quota.** Runners share IP addresses, so Launch Library 2's 15 requests an hour may already be in use. Ingest then ends that source's run as `partial` instead of waiting more than 120 seconds, and the next run resumes from the watermark.
- **Failures** email the person who last changed the workflow's schedule, and every run is listed under **Actions → Ingest**.
- **Sixty days.** In a public repository, GitHub disables scheduled workflows after 60 days without repository activity. Re-enable it under **Actions → Ingest → Enable workflow** (or push any commit before then).
- **Usage.** Check Neon's **Monitoring** page for storage and compute hours after a few days of runs. Raw retention keeps raw near 100 MB (ADR 0009).

### 6. Check

- `/actuator/health` on the API answers `UP`.
- `/en` and `/ja` on the site show the hero at once and "Waking up the data link" while the API scales up from zero, then the data.

## Updating

- **Web:** `just preview-web` builds against the API's current address, writes the route shells (it reads the agency list from the API) and uploads both.
- **API:** every push to `main` that touches `api/` publishes a new image. Roll it out with `az containerapp update -n hoshizora-api -g hoshizora-preview --image ghcr.io/froxily/hoshizora-api:<commit>`. Automating this and the web upload through GitHub OIDC federated credentials is planned, not built.
- **API restart:** `just preview-api-restart` clears the API's in-memory cache and makes it read changed secrets. Express environments refuse `az containerapp revision restart` (InternalServerError) and `--revision-suffix` (ExpressEnvironmentFeatureNotSupported), and the containerapp CLI extension 1.3.0b5 has no `stop` or `start`. An `az containerapp update --set-env-vars RESTARTED_AT=…` is accepted but leaves the running replica in place; the new settings apply when a replica next starts. So the recipe sets `RESTARTED_AT`, waits without traffic until the old replica scales to zero (about 5 minutes idle), wakes a new one, and checks that it is newer than the update, healthy and reading the database. It takes up to about 12 minutes.
- **Data:** the Ingest workflow keeps it current. `just preview-load` only seeds a fresh, empty database from a local one.

## Behaviour on the free tier

- **Cold start.** With no traffic the API scales to zero. The first request starts a replica and waits for it; measured on the preview, health answered in about 4 s from cold. Meanwhile the site stays usable and says it is waking the data link.
- **Neon cold start.** The database also scales to zero; its first query adds well under a second.
- **A failed pull sticks to its image reference.** While the package was still private, a pull of one commit tag failed, and that app kept failing on that exact reference after the package went public. Fresh apps and other tags pulled fine.

## Files

| File | Purpose |
|---|---|
| `.github/workflows/api-image.yml` | Builds `api/Dockerfile` and pushes it to GHCR, tagged with the commit and `latest` |
| `.github/workflows/ingest.yml` | `ingest-all` every 6 hours against the preview database, with a `reviewed` input for held sources |
| `web/scripts/route-shells.ts`, `web/scripts/routeShells.ts` | Route shells for HTTP 200 deep links |
| `justfile` (`preview-migrate`, `preview-load`, `preview-refresh`, `preview-secrets`, `preview-ingest-secret`, `preview-ingest-setup`, `preview-web`) | The preview steps that run on your machine |
| `api/Dockerfile` | Multi-stage build on Temurin 25.0.4: Gradle `bootJar`, extracted jar, non-root user, an AOT cache from a training run, memory flags |
| `api/src/main/resources/application-preview.yaml` | Datasource from `DATABASE_URL` / `DATABASE_USER` / `DATABASE_PASSWORD`, a small Hikari pool, `PORT` |
| `infra/docker-compose.yml` (`preview-flyway`, `preview-load`, `preview-refresh`) and `infra/preview/` | Migrations, the one-shot data copy and the mart refresh against `PREVIEW_DATABASE_URL`, run in containers so they behave the same on Windows, macOS and Linux |

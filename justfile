set dotenv-load := true
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

compose := "docker compose -f infra/docker-compose.yml"
preview_site := "https://hoshizorapreview.z48.web.core.windows.net"
actionlint := "rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667"
gradlew := if os_family() == "windows" { ".\\gradlew.bat" } else { "./gradlew" }
local_ingest_url := "postgresql://hoshizora_ingest:" + env("HOSHIZORA_INGEST_DB_PASSWORD", "hoshizora_ingest_dev") + "@localhost:" + env("POSTGRES_PORT", "5432") + "/" + env("POSTGRES_DB", "hoshizora")

export HOSHIZORA_INGEST_DATABASE_URL := env("HOSHIZORA_INGEST_DATABASE_URL", local_ingest_url)
export HOSHIZORA_LL2_BASE_URL := env("HOSHIZORA_LL2_BASE_URL", "https://ll.thespacedevs.com")

[doc("List every recipe")]
default:
    @just --list --unsorted

[doc("Start PostgreSQL and wait until it is healthy")]
up:
    {{ compose }} up -d --wait postgres

[doc("Stop the local stack, keeping its data")]
down:
    {{ compose }} down

[doc("Apply Flyway migrations, plus local login roles")]
migrate:
    {{ compose }} run --rm flyway migrate

[doc("Apply the migrations and login roles to the preview database (PREVIEW_* variables, see docs/deploy.md)")]
preview-migrate:
    {{ compose }} --profile preview run --rm preview-flyway migrate

[doc("Store the Neon owner connection string from a hidden prompt, encrypted for this Windows user, so preview-schema can run unattended")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
preview-access:
    $ErrorActionPreference = 'Stop'
    $secure = Read-Host 'Neon connection string (owner, direct)' -AsSecureString
    $env:PROBE_URL = [Net.NetworkCredential]::new('', $secure).Password
    if ($env:PROBE_URL -notmatch '^postgres(ql)?://[^@]+@.+$') { throw 'The connection string must look like postgresql://user:password@host/db?sslmode=require' }
    'checking the connection'
    docker run --rm -e PROBE_URL postgres:18.6-trixie sh -c 'psql "$PROBE_URL" -tAc "SELECT current_user"'
    if ($LASTEXITCODE) { throw "the connection check failed with exit code $LASTEXITCODE" }
    $env:PROBE_URL = ''
    $folder = Join-Path $env:LOCALAPPDATA 'Hoshizora'
    New-Item -ItemType Directory -Force $folder | Out-Null
    $secure | ConvertFrom-SecureString | Set-Content -Encoding ascii (Join-Path $folder 'preview-owner.dpapi')
    'stored, encrypted for this Windows user'

[doc("Store the Neon owner connection string from a hidden prompt in a file only this user can read, so preview-schema can run unattended")]
[unix]
[script("sh")]
preview-access:
    set -eu
    printf 'Neon connection string (owner, direct): ' >&2; stty -echo; IFS= read -r url; stty echo; echo >&2
    case "$url" in postgres://*@*|postgresql://*@*) ;; *) echo 'The connection string must look like postgresql://user:password@host/db?sslmode=require' >&2; exit 2 ;; esac
    echo 'checking the connection'
    PROBE_URL=$url docker run --rm -e PROBE_URL postgres:18.6-trixie sh -c 'psql "$PROBE_URL" -tAc "SELECT current_user"'
    folder="${XDG_CONFIG_HOME:-$HOME/.config}/hoshizora"
    mkdir -p "$folder"
    (umask 077; printf '%s' "$url" > "$folder/preview-owner")
    echo 'stored for this user'

[doc("Apply new versioned migrations to the preview database, leaving the login roles untouched; reads the connection stored by preview-access")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
preview-schema:
    $ErrorActionPreference = 'Stop'
    if (-not $env:PREVIEW_DATABASE_URL) {
        $stored = Join-Path $env:LOCALAPPDATA 'Hoshizora\preview-owner.dpapi'
        if (-not (Test-Path $stored)) { throw 'No stored preview access: run just preview-access first' }
        $env:PREVIEW_DATABASE_URL = [Net.NetworkCredential]::new('', (Get-Content $stored | ConvertTo-SecureString)).Password
    }
    {{ compose }} --profile preview run --rm -e FLYWAY_LOCATIONS=filesystem:/flyway/sql -e 'FLYWAY_IGNORE_MIGRATION_PATTERNS=*:missing' -e FLYWAY_PLACEHOLDERS_API_PASSWORD=unused -e FLYWAY_PLACEHOLDERS_INGEST_PASSWORD=unused preview-flyway migrate
    if ($LASTEXITCODE) { throw "flyway failed with exit code $LASTEXITCODE" }

[doc("Apply new versioned migrations to the preview database, leaving the login roles untouched; reads the connection stored by preview-access")]
[unix]
[script("sh")]
preview-schema:
    set -eu
    if [ -z "${PREVIEW_DATABASE_URL:-}" ]; then
        stored="${XDG_CONFIG_HOME:-$HOME/.config}/hoshizora/preview-owner"
        [ -f "$stored" ] || { echo 'No stored preview access: run just preview-access first' >&2; exit 2; }
        PREVIEW_DATABASE_URL=$(cat "$stored"); export PREVIEW_DATABASE_URL
    fi
    {{ compose }} --profile preview run --rm -e FLYWAY_LOCATIONS=filesystem:/flyway/sql -e 'FLYWAY_IGNORE_MIGRATION_PATTERNS=*:missing' -e FLYWAY_PLACEHOLDERS_API_PASSWORD=unused -e FLYWAY_PLACEHOLDERS_INGEST_PASSWORD=unused preview-flyway migrate

[doc("Copy the local database's data into a freshly migrated preview database (see docs/deploy.md)")]
preview-load:
    {{ compose }} --profile preview run --rm preview-load

[doc("Refresh every mart in the preview database, in the order ingest uses (see docs/deploy.md)")]
preview-refresh:
    {{ compose }} --profile preview run --rm preview-refresh

[doc("Build the web app against the preview API, write a route shell per page and agency, and upload everything to the preview storage website (needs az login, see docs/deploy.md)")]
preview-web $VITE_API_BASE_URL=("https://" + shell("az containerapp show -n hoshizora-api -g hoshizora-preview --query properties.configuration.ingress.fqdn -o tsv")): web-deps
    pnpm --dir web build
    node web/scripts/route-shells.ts --api {{ VITE_API_BASE_URL }} --site {{ preview_site }}
    az storage blob upload-batch --account-name hoshizorapreview --auth-mode key --source web/dist --destination '$web' --overwrite --content-cache-control "public, max-age=31536000, immutable" --only-show-errors -o none
    az storage blob upload --account-name hoshizorapreview --auth-mode key --container-name '$web' --file web/dist/index.html --name index.html --overwrite --content-type "text/html; charset=utf-8" --content-cache-control no-cache --only-show-errors -o none
    az storage blob upload-batch --account-name hoshizorapreview --auth-mode key --source web/dist-shells/depth-1 --destination '$web' --overwrite --content-type "text/html; charset=utf-8" --content-cache-control no-cache --only-show-errors -o none
    az storage blob upload-batch --account-name hoshizorapreview --auth-mode key --source web/dist-shells/depth-2 --destination '$web' --overwrite --content-type "text/html; charset=utf-8" --content-cache-control no-cache --only-show-errors -o none
    az storage blob upload-batch --account-name hoshizorapreview --auth-mode key --source web/dist-shells/depth-3 --destination '$web' --overwrite --content-type "text/html; charset=utf-8" --content-cache-control no-cache --only-show-errors -o none

[doc("Store the preview API's database password as a Container App secret, from this terminal session or a hidden prompt (see docs/deploy.md)")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
preview-secrets:
    $ErrorActionPreference = 'Stop'
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) { $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') }
    function Read-Secret([string] $prompt) { [Net.NetworkCredential]::new('', (Read-Host $prompt -AsSecureString)).Password }
    $dbPassword = if ($env:PREVIEW_API_DB_PASSWORD) { $env:PREVIEW_API_DB_PASSWORD } else { Read-Secret 'hoshizora_api database password' }
    az containerapp secret set -n hoshizora-api -g hoshizora-preview --secrets "db-password=$dbPassword" -o none --only-show-errors
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    'stored'

[doc("Store the preview API's database password as a Container App secret, from this terminal session or a hidden prompt (see docs/deploy.md)")]
[unix]
[script("sh")]
preview-secrets:
    set -eu
    read_secret() { printf '%s: ' "$1" >&2; stty -echo; IFS= read -r value; stty echo; echo >&2; printf '%s' "$value"; }
    db_password=${PREVIEW_API_DB_PASSWORD:-$(read_secret 'hoshizora_api database password')}
    az containerapp secret set -n hoshizora-api -g hoshizora-preview --secrets "db-password=$db_password" -o none --only-show-errors
    echo stored

[doc("Capture the README screenshots (WebP) and demo GIF from the live preview (needs ffmpeg and cwebp on PATH)")]
readme-media: web-deps
    node web/scripts/readme-media.ts --site {{ preview_site }}

[doc("Restart the preview API so it reads its current secrets: set RESTARTED_AT, wait (sending no traffic) until the old replica scales to zero, then wake a new one and check it reads the database. Takes up to about 12 minutes")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
preview-api-restart:
    $ErrorActionPreference = 'Stop'
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) { $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') }
    $app = @('-n', 'hoshizora-api', '-g', 'hoshizora-preview')
    function Get-ReplicaTimes { $revision = az containerapp show @app --query properties.latestRevisionName -o tsv --only-show-errors; @(az containerapp replica list @app --revision $revision --query '[].properties.createdTime' -o tsv --only-show-errors | Where-Object { $_ }) }
    $stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    az containerapp update @app --set-env-vars "RESTARTED_AT=$stamp" -o none --only-show-errors
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    $fqdn = az containerapp show @app --query properties.configuration.ingress.fqdn -o tsv --only-show-errors
    'waiting for the old replica to scale to zero (express environments keep it running; up to 10 minutes without traffic)'
    foreach ($attempt in 1..40) {
        if (@(Get-ReplicaTimes | Where-Object { $_ -lt $stamp }).Count -eq 0) { break }
        if ($attempt -eq 40) { throw 'An old replica is still running after 10 minutes; something keeps sending traffic. Run this again later.' }
        Start-Sleep -Seconds 15
    }
    'waking the API'
    foreach ($attempt in 1..24) {
        $health = curl.exe -fs -m 60 "https://$fqdn/actuator/health"
        if (-not $LASTEXITCODE -and "$health" -match '"status":"UP"') {
            curl.exe -fs -m 60 -o NUL "https://$fqdn/api/v1/meta/sources"
            $times = Get-ReplicaTimes
            if (-not $LASTEXITCODE -and $times.Count -gt 0 -and @($times | Where-Object { $_ -lt $stamp }).Count -eq 0) { "API restarted after $stamp, healthy and reading the database"; exit 0 }
        }
        Start-Sleep -Seconds 5
    }
    throw 'The new replica did not become healthy within 2 minutes; check the Container App in the Azure portal'

[doc("Restart the preview API so it reads its current secrets: set RESTARTED_AT, wait (sending no traffic) until the old replica scales to zero, then wake a new one and check it reads the database. Takes up to about 12 minutes")]
[unix]
[script("sh")]
preview-api-restart:
    set -eu
    replica_times() {
        revision=$(az containerapp show -n hoshizora-api -g hoshizora-preview --query properties.latestRevisionName -o tsv --only-show-errors)
        az containerapp replica list -n hoshizora-api -g hoshizora-preview --revision "$revision" --query '[].properties.createdTime' -o tsv --only-show-errors
    }
    older_than_stamp() { for created in $(replica_times); do [ "$(printf '%s\n%s\n' "$created" "$stamp" | sort | head -n 1)" = "$created" ] && [ "$created" != "$stamp" ] && return 0; done; return 1; }
    stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    az containerapp update -n hoshizora-api -g hoshizora-preview --set-env-vars "RESTARTED_AT=$stamp" -o none --only-show-errors
    fqdn=$(az containerapp show -n hoshizora-api -g hoshizora-preview --query properties.configuration.ingress.fqdn -o tsv --only-show-errors)
    echo 'waiting for the old replica to scale to zero (express environments keep it running; up to 10 minutes without traffic)'
    attempt=0
    while older_than_stamp; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 40 ]; then echo 'An old replica is still running after 10 minutes; something keeps sending traffic. Run this again later.' >&2; exit 1; fi
        sleep 15
    done
    echo 'waking the API'
    for attempt in $(seq 1 24); do
        if curl -fs -m 60 "https://$fqdn/actuator/health" | grep -q '"status":"UP"' && curl -fs -m 60 -o /dev/null "https://$fqdn/api/v1/meta/sources" && [ -n "$(replica_times)" ] && ! older_than_stamp; then
            echo "API restarted after $stamp, healthy and reading the database"; exit 0
        fi
        sleep 5
    done
    echo 'The new replica did not become healthy within 2 minutes; check the Container App in the Azure portal' >&2; exit 1

[doc("Store the ingest login's preview database URL as the repository secret the scheduled ingestion uses; on its own it first gives the login a fresh password and checks it (see docs/deploy.md)")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
preview-ingest-secret:
    $ErrorActionPreference = 'Stop'
    function Read-Secret([string] $prompt) { [Net.NetworkCredential]::new('', (Read-Host $prompt -AsSecureString)).Password }
    function Assert-Step([string] $step) { if ($LASTEXITCODE) { throw "$step failed with exit code $LASTEXITCODE" } }
    if (-not $env:PREVIEW_DATABASE_URL) { $env:PREVIEW_DATABASE_URL = Read-Secret 'Neon connection string (owner, direct)' }
    if ($env:PREVIEW_DATABASE_URL -notmatch '^postgres(ql)?://[^@]+@(.+)$') { throw 'The connection string must look like postgresql://user:password@host/db?sslmode=require' }
    $location = $Matches[2]
    if (-not $env:PREVIEW_INGEST_DB_PASSWORD) {
        $bytes = [byte[]]::new(24); [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $env:NEW_PASSWORD = -join ($bytes | ForEach-Object { $_.ToString('x2') })
        'giving hoshizora_ingest a new password'
        "ALTER ROLE hoshizora_ingest WITH LOGIN PASSWORD :'pw';" | docker run --rm -i -e PREVIEW_DATABASE_URL -e NEW_PASSWORD postgres:18.6-trixie sh -c 'psql "$PREVIEW_DATABASE_URL" -q -v ON_ERROR_STOP=1 -v pw="$NEW_PASSWORD"'
        Assert-Step 'ALTER ROLE'
        $env:PREVIEW_INGEST_DB_PASSWORD = $env:NEW_PASSWORD
        $env:NEW_PASSWORD = ''
    }
    'checking the hoshizora_ingest login'
    $env:PROBE_URL = "postgresql://hoshizora_ingest:$($env:PREVIEW_INGEST_DB_PASSWORD)@$location"
    docker run --rm -e PROBE_URL postgres:18.6-trixie sh -c 'psql "$PROBE_URL" -tAc "SELECT current_user"'; Assert-Step 'login hoshizora_ingest'
    'storing the GitHub secret'
    $env:PROBE_URL | gh secret set PREVIEW_INGEST_DATABASE_URL; Assert-Step 'gh secret set'
    $env:PROBE_URL = ''
    'stored: merge the pull request, then run Actions > Ingest > Run workflow once'

[doc("Store the ingest login's preview database URL as the repository secret the scheduled ingestion uses; on its own it first gives the login a fresh password and checks it (see docs/deploy.md)")]
[unix]
[script("sh")]
preview-ingest-secret:
    set -eu
    if [ -z "${PREVIEW_DATABASE_URL:-}" ]; then printf 'Neon connection string (owner, direct): ' >&2; stty -echo; IFS= read -r PREVIEW_DATABASE_URL; stty echo; echo >&2; fi
    case "$PREVIEW_DATABASE_URL" in postgres://*@*|postgresql://*@*) ;; *) echo 'The connection string must look like postgresql://user:password@host/db?sslmode=require' >&2; exit 2 ;; esac
    export PREVIEW_DATABASE_URL
    if [ -z "${PREVIEW_INGEST_DB_PASSWORD:-}" ]; then
        NEW_PASSWORD=$(openssl rand -hex 24); export NEW_PASSWORD
        echo 'giving hoshizora_ingest a new password'
        printf '%s\n' "ALTER ROLE hoshizora_ingest WITH LOGIN PASSWORD :'pw';" | docker run --rm -i -e PREVIEW_DATABASE_URL -e NEW_PASSWORD postgres:18.6-trixie sh -c 'psql "$PREVIEW_DATABASE_URL" -q -v ON_ERROR_STOP=1 -v pw="$NEW_PASSWORD"'
        PREVIEW_INGEST_DB_PASSWORD=$NEW_PASSWORD
    fi
    echo 'checking the hoshizora_ingest login'
    PROBE_URL="postgresql://hoshizora_ingest:$PREVIEW_INGEST_DB_PASSWORD@${PREVIEW_DATABASE_URL#*@}"; export PROBE_URL
    docker run --rm -e PROBE_URL postgres:18.6-trixie sh -c 'psql "$PROBE_URL" -tAc "SELECT current_user"'
    echo 'storing the GitHub secret'
    printf '%s' "$PROBE_URL" | gh secret set PREVIEW_INGEST_DATABASE_URL
    echo 'stored: merge the pull request, then run Actions > Ingest > Run workflow once'

[doc("Set up scheduled ingestion; safe to rerun: keeps the API's stored database password, gives the ingest login a fresh one, applies new migrations, checks both logins, restarts the API and stores the ingest secret (see docs/deploy.md)")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
preview-ingest-setup:
    $ErrorActionPreference = 'Stop'
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) { $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') }
    function Read-Secret([string] $prompt) { [Net.NetworkCredential]::new('', (Read-Host $prompt -AsSecureString)).Password }
    function New-Password { $bytes = [byte[]]::new(24); [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); -join ($bytes | ForEach-Object { $_.ToString('x2') }) }
    function Assert-Step([string] $step) { if ($LASTEXITCODE) { throw "$step failed with exit code $LASTEXITCODE" } }
    if (-not $env:PREVIEW_DATABASE_URL) { $env:PREVIEW_DATABASE_URL = Read-Secret 'Neon connection string (owner, direct)' }
    if ($env:PREVIEW_DATABASE_URL -notmatch '^postgres(ql)?://[^@]+@(.+)$') { throw 'The connection string must look like postgresql://user:password@host/db?sslmode=require' }
    $location = $Matches[2]
    $stored = az containerapp secret show -n hoshizora-api -g hoshizora-preview --secret-name db-password --query value -o tsv --only-show-errors
    $newApiPassword = $LASTEXITCODE -or -not $stored
    $env:PREVIEW_API_DB_PASSWORD = if ($newApiPassword) { New-Password } else { $stored }
    $env:PREVIEW_INGEST_DB_PASSWORD = New-Password
    if ($newApiPassword) { '1/5 migrating the preview database with new passwords for both logins' } else { "1/5 migrating the preview database; the API keeps its stored password, the ingest login gets a new one" }
    just preview-migrate; Assert-Step 'preview-migrate'
    '2/5 checking both logins'
    foreach ($login in @(@('hoshizora_api', $env:PREVIEW_API_DB_PASSWORD), @('hoshizora_ingest', $env:PREVIEW_INGEST_DB_PASSWORD))) {
        $env:PROBE_URL = "postgresql://$($login[0]):$($login[1])@$location"
        docker run --rm -e PROBE_URL postgres:18.6-trixie sh -c 'psql "$PROBE_URL" -tAc "SELECT current_user"'; Assert-Step "login $($login[0])"
    }
    $env:PROBE_URL = ''
    if ($newApiPassword) { '3/5 storing the API password'; just preview-secrets; Assert-Step 'preview-secrets' } else { '3/5 the API password is already stored' }
    '4/5 restarting the API'
    just preview-api-restart; Assert-Step 'preview-api-restart'
    '5/5 storing the ingest secret in GitHub'
    just preview-ingest-secret; Assert-Step 'preview-ingest-secret'
    'done: merge the pull request, then run Actions > Ingest > Run workflow once'

[doc("Set up scheduled ingestion; safe to rerun: keeps the API's stored database password, gives the ingest login a fresh one, applies new migrations, checks both logins, restarts the API and stores the ingest secret (see docs/deploy.md)")]
[unix]
[script("sh")]
preview-ingest-setup:
    set -eu
    if [ -z "${PREVIEW_DATABASE_URL:-}" ]; then printf 'Neon connection string (owner, direct): ' >&2; stty -echo; IFS= read -r PREVIEW_DATABASE_URL; stty echo; echo >&2; fi
    case "$PREVIEW_DATABASE_URL" in postgres://*@*|postgresql://*@*) ;; *) echo 'The connection string must look like postgresql://user:password@host/db?sslmode=require' >&2; exit 2 ;; esac
    location=${PREVIEW_DATABASE_URL#*@}
    new_api_password=false
    PREVIEW_API_DB_PASSWORD=$(az containerapp secret show -n hoshizora-api -g hoshizora-preview --secret-name db-password --query value -o tsv --only-show-errors 2>/dev/null || true)
    if [ -z "$PREVIEW_API_DB_PASSWORD" ]; then PREVIEW_API_DB_PASSWORD=$(openssl rand -hex 24); new_api_password=true; fi
    PREVIEW_INGEST_DB_PASSWORD=$(openssl rand -hex 24)
    export PREVIEW_DATABASE_URL PREVIEW_API_DB_PASSWORD PREVIEW_INGEST_DB_PASSWORD
    echo '1/5 migrating the preview database (the ingest login gets a new password)'
    just preview-migrate
    echo '2/5 checking both logins'
    for login in "hoshizora_api:$PREVIEW_API_DB_PASSWORD" "hoshizora_ingest:$PREVIEW_INGEST_DB_PASSWORD"; do
        PROBE_URL="postgresql://$login@$location" docker run --rm -e PROBE_URL postgres:18.6-trixie sh -c 'psql "$PROBE_URL" -tAc "SELECT current_user"'
    done
    if [ "$new_api_password" = true ]; then echo '3/5 storing the API password'; just preview-secrets; else echo '3/5 the API password is already stored'; fi
    echo '4/5 restarting the API'
    just preview-api-restart
    echo '5/5 storing the ingest secret in GitHub'
    just preview-ingest-secret
    echo 'done: merge the pull request, then run Actions > Ingest > Run workflow once'

[doc("Store the api.nasa.gov key from a hidden prompt: checks it with NASA, then saves it as the HOSHIZORA_NASA_API_KEY repository secret and in .env")]
[windows]
[script("powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File")]
[extension(".ps1")]
nasa-key:
    $ErrorActionPreference = 'Stop'
    $key = [Net.NetworkCredential]::new('', (Read-Host 'api.nasa.gov key' -AsSecureString)).Password.Trim()
    if ($key -notmatch '^[A-Za-z0-9]{20,64}$') { throw 'An api.nasa.gov key is 40 letters and digits' }
    if ($key -eq 'DEMO_KEY') { throw 'DEMO_KEY is shared per IP; register a key at api.nasa.gov' }
    'checking the key with api.nasa.gov'
    $headers = "X-Api-Key: $key" | curl.exe -s -m 30 -o NUL -D - -H '@-' 'https://api.nasa.gov/neo/rest/v1/stats'
    $status = ($headers | Select-String '^HTTP/\S+ (\d+)' | Select-Object -Last 1).Matches.Groups[1].Value
    $limit = ($headers | Select-String '(?i)^X-RateLimit-Limit: (\d+)' | Select-Object -Last 1).Matches.Groups[1].Value
    if ($status -ne '200') { throw "api.nasa.gov answered HTTP $status; check the key" }
    "accepted, hourly limit $limit"
    'storing the GitHub secret'
    $key | gh secret set HOSHIZORA_NASA_API_KEY
    if ($LASTEXITCODE) { throw "gh secret set failed with exit code $LASTEXITCODE" }
    'storing it in .env'
    $envFile = Join-Path '{{ justfile_directory() }}' '.env'
    $lines = if (Test-Path $envFile) { @(Get-Content $envFile | Where-Object { $_ -notmatch '^HOSHIZORA_NASA_API_KEY=' }) } else { @() }
    [IO.File]::WriteAllLines($envFile, [string[]]($lines + "HOSHIZORA_NASA_API_KEY=$key"), [Text.UTF8Encoding]::new($false))
    'stored'

[doc("Store the api.nasa.gov key from a hidden prompt: checks it with NASA, then saves it as the HOSHIZORA_NASA_API_KEY repository secret and in .env")]
[unix]
[script("sh")]
nasa-key:
    set -eu
    printf 'api.nasa.gov key: ' >&2; stty -echo; IFS= read -r key; stty echo; echo >&2
    case "$key" in DEMO_KEY) echo 'DEMO_KEY is shared per IP; register a key at api.nasa.gov' >&2; exit 2 ;; *[!A-Za-z0-9]*|'') echo 'An api.nasa.gov key is 40 letters and digits' >&2; exit 2 ;; esac
    echo 'checking the key with api.nasa.gov'
    status=$(printf 'X-Api-Key: %s\n' "$key" | curl -s -m 30 -o /dev/null -w '%{http_code}' -H @- https://api.nasa.gov/neo/rest/v1/stats)
    if [ "$status" != 200 ]; then echo "api.nasa.gov answered HTTP $status; check the key" >&2; exit 1; fi
    echo 'storing the GitHub secret'
    printf '%s' "$key" | gh secret set HOSHIZORA_NASA_API_KEY
    echo 'storing it in .env'
    env_file="{{ justfile_directory() }}/.env"
    touch "$env_file"
    { grep -v '^HOSHIZORA_NASA_API_KEY=' "$env_file" || true; printf 'HOSHIZORA_NASA_API_KEY=%s\n' "$key"; } > "$env_file.tmp"
    mv "$env_file.tmp" "$env_file"
    echo 'stored'

[doc("Ingest one source (--max-requests N caps a run, --max-wait S and --reviewed as for ingest-all)")]
[working-directory("ingest")]
ingest source *flags:
    uv run hoshizora ingest {{ source }} {{ flags }}

[doc("Backfill Launch Library 2 from its production host, run after run, until no pages are left")]
[working-directory("ingest")]
backfill:
    uv run hoshizora backfill --log-file "{{ justfile_directory() }}/logs/backfill.log"

[doc("Show Launch Library 2 backfill progress: launches loaded, pages left, last run, ETA")]
[working-directory("ingest")]
backfill-status:
    uv run hoshizora backfill-status

[doc("Print the data-quality report (pass --strict to fail on blocking problems)")]
[working-directory("ingest")]
dq *flags:
    uv run hoshizora dq {{ flags }}

[doc("Rebuild one source's core rows from its raw payloads")]
[working-directory("ingest")]
replay source:
    uv run hoshizora replay {{ source }}

[doc("Refresh every analytics mart concurrently (ingestion does this after runs that change rows)")]
[working-directory("ingest")]
refresh-marts:
    uv run hoshizora refresh-marts

[doc("Regenerate every fact from the templates in facts/templates (ingestion does this after mart refreshes)")]
[working-directory("ingest")]
facts:
    uv run hoshizora facts

[doc("Ingest every registered source (--max-wait S ends a run as partial instead of waiting longer; --reviewed resumes held sources)")]
[working-directory("ingest")]
ingest-all *flags:
    uv run hoshizora ingest-all {{ flags }}

[doc("Run the API on :8080 against the local database")]
[working-directory("api")]
api:
    {{ gradlew }} bootRun

[doc("Run the web dev server on :5173")]
[working-directory("web")]
web: web-deps
    pnpm dev

[doc("Run the Playwright smoke tests against a production build (API answered from OpenAPI examples)")]
[working-directory("web")]
e2e: web-deps
    pnpm e2e

[doc("Lighthouse every page on mobile and desktop against a production build served by vite preview on :4173 (start it with: just web-preview)")]
[working-directory("web")]
lighthouse: web-deps
    node scripts/lighthouse.mjs

[doc("Build the web app and serve it on :4173, proxying /api to the local API")]
[working-directory("web")]
web-preview: web-deps
    pnpm build
    pnpm preview

[doc("Rewrite api/openapi.yaml from the API, then regenerate the web types")]
api-spec: api-spec-update api-types

[private]
[working-directory("api")]
api-spec-update:
    {{ gradlew }} updateOpenApi

[private]
[working-directory("web")]
api-types: web-deps
    pnpm api:types

[doc("Format every project in place")]
fmt: fmt-ingest fmt-api fmt-web

[doc("Run every test suite")]
test: test-ingest test-api test-web

[doc("Lint, type-check and test everything (what CI runs)")]
check: check-workflows check-ingest check-api check-web

[private]
[working-directory("ingest")]
fmt-ingest:
    uv run ruff format
    uv run ruff check --fix

[private]
[working-directory("api")]
fmt-api:
    {{ gradlew }} spotlessApply

[private]
[working-directory("web")]
fmt-web: web-deps
    pnpm format
    pnpm lint:fix

[private]
[working-directory("ingest")]
test-ingest:
    uv run --locked pytest

[private]
[working-directory("api")]
test-api:
    {{ gradlew }} test

[private]
[working-directory("web")]
test-web: web-deps
    pnpm test

[private]
check-workflows:
    docker run --rm -v "{{ justfile_directory() }}:/repo" -w /repo {{ actionlint }} -color

[private]
[working-directory("ingest")]
check-ingest:
    uv run --locked ruff format --check
    uv run --locked ruff check
    uv run --locked pyright
    uv run --locked pytest

[private]
[working-directory("api")]
check-api:
    {{ gradlew }} check

[private]
[working-directory("web")]
check-web: web-deps
    pnpm lint
    pnpm format:check
    pnpm api:check
    pnpm typecheck
    pnpm test
    pnpm e2e

[private]
[working-directory("web")]
web-deps:
    pnpm install --frozen-lockfile

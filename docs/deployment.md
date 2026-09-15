# ResearchOps AI — How to Run & Deploy

Complete guide to run the project locally, with Docker Compose, and deploy to **AWS EC2** using **Terraform** (infrastructure) → **Ansible** (configure & deploy) → **Docker Compose** (runtime).

```text
Local run  →  Docker Compose  →  GitHub CI  →  Terraform (EC2)  →  Ansible (Docker deploy)
```

---

## Prerequisites

| Tool | Used for |
|---|---|
| Python 3.12+ | Local development |
| Docker Desktop / Docker Engine | Local Compose & EC2 containers |
| Git | Source control |
| AWS CLI | Credentials for Terraform |
| Terraform ≥ 1.5 | Provision EC2 + security group |
| Ansible (WSL/Linux) | Install Docker on EC2 and deploy the stack |
| An EC2 key pair (`.pem`) | SSH into the instance |

**Repo used by Ansible (edit if yours differs):**  
`https://github.com/Niruuu2005/ResearchHUB.git` — set in `ansible/deploy.yml` (`repo_url`).

Replace placeholders everywhere:

- `<KEY_NAME>` — EC2 key pair name **without** `.pem`
- `<KEY_PATH>` — full path to your `.pem` file
- `<EC2_PUBLIC_IP>` — IP from `terraform output public_ip`
- `<YOUR_PUBLIC_IP>` — your IP for SSH lockdown (optional)

---

## Part 1 — Run Locally (Zero Setup)

Uses **SQLite**, in-process PDF work (`USE_CELERY=false`), and hash/sentence-transformers embeddings. No Redis/Postgres required.

### 1.1 Setup

```powershell
cd "d:\7th Sem\DevOps\ResearchHub"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Optional env (copy and edit):

```powershell
Copy-Item .env.example .env
```

Useful variables:

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `heuristic` | `openai` / `gemini` / `ollama` / offline extract |
| `EMBEDDING_PROVIDER` | `auto` | `sentence-transformers` if installed, else hash |
| `USE_CELERY` | `false` | Sync PDF processing in the API process |
| `DATABASE_URL` | SQLite file | Set Postgres URL only if you use an external DB |

### 1.2 Start the API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 1.3 Open these URLs

| URL | Purpose |
|---|---|
| http://localhost:8000 | Web UI |
| http://localhost:8000/docs | Swagger / OpenAPI |
| http://localhost:8000/health | Liveness |
| http://localhost:8000/ready | Readiness |
| http://localhost:8000/metrics | Prometheus text |

### 1.4 Run tests

```powershell
python -m pytest tests/ -v
```

Expect **33 passed** (count may grow as tests are added).

---

## Part 2 — Run with Docker Compose (Full Stack)

Starts **API**, **Celery worker**, **PostgreSQL** (pgvector image), **Redis**, **Prometheus**, **Grafana**, and **Nginx** gateway.

### 2.1 Start

```powershell
cd "d:\7th Sem\DevOps\ResearchHub"

# Free port 8000 if a local uvicorn is still running
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

docker compose up --build -d
docker compose ps
```

Compose sets `USE_CELERY=true` and `EMBEDDING_PROVIDER=auto`.  
The API container runs `alembic upgrade head` on startup (no separate migrate step).

### 2.2 Check status

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/ready
```

### 2.3 Service URLs

| Service | URL |
|---|---|
| UI / API | http://localhost:8000 |
| Nginx gateway | http://localhost:8080 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (`admin` / `admin`) |
| PostgreSQL / Redis | internal Docker network only (not published on host) |

### 2.4 Stop

```powershell
docker compose down
```

To also remove volumes (DB, docs, exports):

```powershell
docker compose down -v
```

---

## Part 3 — Deploy to AWS (Terraform → EC2 → Ansible → Docker)

### Deployment order

| Step | Tool | What it does |
|---|---|---|
| 1 | GitHub | Store code; CI builds & tests |
| 2 | Docker (local optional) | Prove the image builds before cloud |
| 3 | Terraform | Create Ubuntu EC2 + security group |
| 4 | Ansible | Install Docker on EC2, clone repo, `docker compose up` |
| 5 | Browser | Open `http://<EC2_PUBLIC_IP>` |

> **Instance size:** Default Terraform type is `t3.micro` (Free Tier friendly). The full Compose stack (API + worker + Postgres + Redis + Prometheus + Grafana + Nginx) is heavy — prefer **`t3.small`** or **`t3.medium`** for a reliable demo. Change `instance_type` in `terraform.tfvars`.

---

### Step A — Push code & wait for CI

```powershell
git status
git add .
git commit -m "Prepare ResearchOps for EC2 deployment"
git push origin main
```

Open GitHub → **Actions** → confirm **ResearchOps AI CI/CD Pipeline** is green.

Ensure `ansible/deploy.yml` `repo_url` matches the GitHub repo Ansible should clone.

---

### Step B — (Optional) Verify Docker build locally

```powershell
docker build -t researchops-api:latest -f Dockerfile .
docker build -t researchops-worker:latest -f Dockerfile.worker .
docker compose up --build -d
curl.exe http://localhost:8000/health
docker compose down
```

---

### Step C — AWS preparation

1. Configure credentials:

```powershell
aws configure
```

Use region e.g. `ap-south-1` (must match Terraform).

2. Create an EC2 key pair in the AWS Console (same region):

- **EC2 → Key pairs → Create key pair**
- Name: e.g. `researchops-key`
- Format: `.pem`
- Save the file privately (never commit it)

```powershell
# Example on Windows after download
icacls "C:\Users\<you>\.ssh\researchops-key.pem" /inheritance:r
icacls "C:\Users\<you>\.ssh\researchops-key.pem" /grant:r "%USERNAME%:R"
```

---

### Step D — Terraform (create EC2)

```powershell
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
aws_region       = "ap-south-1"
instance_type    = "t3.small"          # or t3.micro for Free Tier only
key_name         = "researchops-key"   # WITHOUT .pem
allowed_ssh_cidr = "0.0.0.0/0"         # better: "YOUR.IP.HERE/32"
project_name     = "ResearchOpsAI"
```

Apply:

```powershell
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Type `yes` when prompted.

Save outputs:

```powershell
terraform output public_ip
terraform output application_url
terraform output api_url
terraform output grafana_url
```

Security group opens:

| Port | Service |
|---|---|
| 22 | SSH |
| 80 | Nginx gateway |
| 443 | HTTPS (reserved) |
| 8000 | FastAPI direct |
| 9090 | Prometheus (SSH CIDR) |
| 3001 | Grafana |

---

### Step E — Ansible (configure EC2 & deploy Compose)

Ansible is easiest from **WSL** or Linux (not native Windows).

```bash
cd "/mnt/d/7th Sem/DevOps/ResearchHub/ansible"
cp inventory.ini.example inventory.ini
```

Edit `inventory.ini`:

```ini
[research_server]
<EC2_PUBLIC_IP> ansible_user=ubuntu ansible_ssh_private_key_file=<KEY_PATH> ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

Example:

```ini
[research_server]
13.234.12.34 ansible_user=ubuntu ansible_ssh_private_key_file=/mnt/c/Users/you/.ssh/researchops-key.pem ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

Fix key permissions and test SSH:

```bash
chmod 400 <KEY_PATH>
ansible all -i inventory.ini -m ping
```

Deploy (installs Docker + Git, clones/pulls repo to `/opt/researchhub`, runs `docker compose up --build -d`, tries Alembic, checks `/health` and `/ready`):

```bash
ansible-playbook -i inventory.ini deploy.yml
```

First deploy can take several minutes while images build on the instance.

---

### Step F — Verify the live deployment

From your laptop:

```powershell
curl.exe http://<EC2_PUBLIC_IP>/health
curl.exe http://<EC2_PUBLIC_IP>:8000/ready
curl.exe http://<EC2_PUBLIC_IP>:8000/metrics
```

Open in a browser:

| URL | What |
|---|---|
| http://\<EC2_PUBLIC_IP\> | UI via Nginx |
| http://\<EC2_PUBLIC_IP\>:8000 | API + UI direct |
| http://\<EC2_PUBLIC_IP\>:8000/docs | Swagger |
| http://\<EC2_PUBLIC_IP\>:3001 | Grafana (`admin` / `admin`) |
| http://\<EC2_PUBLIC_IP\>:9090 | Prometheus (if your IP is allowed) |

SSH inspect:

```bash
ssh -i <KEY_PATH> ubuntu@<EC2_PUBLIC_IP>
cd /opt/researchhub
docker compose ps
docker compose logs -f api
```

---

### Step G — Redeploy after code changes

```powershell
git push origin main
```

Then from WSL:

```bash
cd "/mnt/d/7th Sem/DevOps/ResearchHub/ansible"
ansible-playbook -i inventory.ini deploy.yml
```

Ansible pulls `main` and rebuilds Compose on the same EC2 host.

---

### Step H — Cleanup (stop AWS charges)

```powershell
cd terraform
terraform destroy
```

Type `yes`. This terminates the EC2 instance and deletes the security group.

Also delete unused key pairs / Elastic IPs in the AWS Console if you created extras.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Terraform: key pair not found | Create the key in the **same region** as `aws_region` |
| Ansible ping fails | Check SG port 22, key path, `chmod 400`, and that IP matches Terraform output |
| `/ready` degraded | Wait for Postgres health; API auto-runs Alembic on start — check `docker compose logs api` |
| OOM / containers dying | Use larger instance (`t3.small`+) or stop Grafana/Prometheus temporarily |
| Ansible clones wrong repo | Edit `repo_url` in `ansible/deploy.yml` |
| Port 80 fails locally | On Windows, another app may hold 80; use `:8000` or stop that app |
| Embeddings slow on first request | sentence-transformers downloads the model once |

More detail: [troubleshooting.md](troubleshooting.md).

---

## Related docs

| Doc | Content |
|---|---|
| [deployment-commands.md](deployment-commands.md) | Short command cheat sheet |
| [architecture.md](architecture.md) | System design |
| [api.md](api.md) | REST API reference |
| [viva.md](viva.md) | Oral exam Q&A |

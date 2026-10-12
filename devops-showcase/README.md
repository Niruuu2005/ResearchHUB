# ResearchHub / ResearchOps AI — DevOps Architecture & Implementation Showcase

An interactive, high-fidelity **DevOps Implementation Showcase** and **Viva Presentation Dashboard** built inside the ResearchHub repository.

This independent service visually demonstrates how modern DevOps practices—CI/CD, Infrastructure as Code, Configuration Management, Containerization, Kubernetes Orchestration, Observability, and Reliability Engineering—are implemented in this real-world scholarly AI platform.

---

## 🌟 Key Features

1. **Interactive End-to-End Architecture Map**:
   - Complete lifecycle: `Developer` → `GitHub` → `GitHub Actions` → `Terraform` → `AWS EC2` → `Ansible` → `Docker Compose` → `FastAPI Stack` → `Prometheus & Grafana`.
   - Separate lane for **Kubernetes & Kustomize** orchestration.
   - Interactive Component Inspector displaying verified file paths, configuration snippets, key CLI commands, and examiner defense answers.

2. **Interactive Stage Simulators**:
   - **GitHub Actions (CI)**: Simulates push triggers, Ruff linting, 33 Pytests with coverage, and Docker Buildx image compilation with passing/failing scenarios.
   - **Terraform (IaC)**: Step-by-step CLI simulator (`init`, `validate`, `plan`, `apply`, `destroy`) showing declarative AWS provisioning for `ap-south-1`.
   - **Ansible (Deploy)**: 13-stage animated deployment timeline walkthrough with step-by-step progress and terminal logs.
   - **Docker Multi-Container Grid**: Inspects all 8 container services, image tags, volumes, health checks, and service dependencies.
   - **Kubernetes HPA Simulator**: Interactive workload slider (0–1000 RPS) dynamically demonstrating replica autoscaling between 2 and 8 pods based on 70% CPU target.
   - **Circuit Breaker Sandbox**: Interactive 3-state state machine (`CLOSED` → `OPEN` → `HALF-OPEN`) protecting OpenAlex, Crossref, and Wikipedia APIs (`app/utils/circuit_breaker.py`).
   - **Prometheus & Grafana Dashboard**: Live visual timeseries charts rendering real gauges tracked in `monitoring/grafana/dashboards/researchops.json`.

3. **Live Diagnostic Probes**:
   - Non-invasive read-only HTTP health probes checking `/health`, `/ready`, and `/metrics`.
   - Clear distinction between **Configured**, **Running**, **Simulated**, and **Unavailable** states.

4. **Academic Viva Defense Mode**:
   - Fullscreen 12-slide presentation deck designed for technical vivas and project demonstrations on projectors.
   - Presenter Viva Notes box on every slide detailing exact talking points for examiners.
   - Full keyboard navigation: `→` (Next), `←` (Prev), `Esc` (Exit).

---

## 🚀 Running the Showcase

### Option 1: Run with Docker Compose (Recommended)

The showcase is defined as the `devops-showcase` service in `docker-compose.yml`.

To build and start **only the showcase service**:

```bash
# Start showcase independently on port 8085
docker compose up -d --build devops-showcase

# Verify running container
docker compose ps devops-showcase
```

To start the **entire ResearchOps platform stack** (FastAPI, Worker, Postgres, Redis, Prometheus, Grafana, Gateway, Showcase):

```bash
docker compose up -d --build
```

Access the showcase in your browser:
👉 **`http://localhost:8085`**

---

### Option 2: Run Locally with Python (Zero Setup / Host Testing)

If Docker is not currently running on your host machine, you can launch the showcase directly using Python's built-in HTTP server:

```powershell
# From the repository root:
cd "d:\7th Sem\DevOps\ResearchHub\devops-showcase"
python -m http.server 8085
```

Open in your browser:
👉 **`http://localhost:8085`**

---

## ☁️ Running on AWS EC2

When deploying to AWS EC2 using Terraform and Ansible:

1. **Verify Security Group**:
   Ensure `terraform/main.tf` or your EC2 Security Group permits ingress on port `8085` (or access it over an SSH tunnel / VPN for restricted viva presentations):

   ```hcl
   ingress {
     description = "DevOps Showcase Presentation UI"
     from_port   = 8085
     to_port     = 8085
     protocol    = "tcp"
     cidr_blocks = ["YOUR.IP.HERE/32"] # Restrict to your presenter IP
   }
   ```

2. **Ansible Deployment**:
   Ansible pulls the repository to `/opt/researchhub` and runs `docker compose up --build -d`, which automatically launches `devops-showcase` alongside the main stack.

3. **Access URL**:
   👉 `http://<EC2_PUBLIC_IP>:8085`

---

## 🔒 Security & Safe Execution Design

- **Pure Read-Only Educational Presentation**: No controls execute destructive cloud commands (`terraform apply`, `terraform destroy`, `rm`, etc.).
- **No Secrets Exposed**: All sensitive credentials, database passwords, and `.env` secrets have been omitted or redacted.
- **Docker Isolation**: The showcase runs in an unprivileged Alpine container with no Docker socket (`/var/run/docker.sock`) mounted.
- **Independent Failure Domain**: The showcase functions independently even if the backend FastAPI application or PostgreSQL database is stopped.

---

## 📂 File Structure

```text
devops-showcase/
├── Dockerfile           # Lightweight nginx:alpine container definition
├── nginx.conf           # Reverse proxy configuration with /api-proxy/ and SPA fallback
├── index.html           # Command-center dashboard and 12-slide presentation structure
├── styles.css           # Premium dark-navy technical design system
├── script.js            # Interactive simulators, Canvas charts, probes, and slide controller
├── data/
│   └── project-config.json # Verified repository parameters (IaC, CI, K8s, metrics)
└── README.md            # Execution and architecture documentation
```

---

## 🎓 Viva Presentation Shortcut Reference

| Key | Action |
|---|---|
| `→` or `Space` | Next Presentation Slide |
| `←` | Previous Presentation Slide |
| `Esc` | Exit Fullscreen Presentation Mode |
| `Top-Right Button` | Toggle Fullscreen Viva Deck |

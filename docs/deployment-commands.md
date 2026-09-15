# ResearchOps AI — Simple Commands

Order: **Local → Docker → GitHub → Terraform → Ansible → Cleanup**

Replace: `YOUR_KEY` (EC2 key name, no `.pem`), `PATH/TO/key.pem`, `EC2_IP`

---

## 1. Local (PowerShell)

Stop anything already on port 8000 first if needed.

```powershell
cd "d:\7th Sem\DevOps\ResearchHub"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open: http://127.0.0.1:8000

```powershell
pytest -q
```

---

## 2. Docker Compose (PowerShell)

**Start Docker Desktop first** and wait until it says *Docker Desktop is running* (whale icon steady).

Check engine:

```powershell
docker version
```

If you see `500 Internal Server Error` / `dockerDesktopLinuxEngine`, Docker is not ready:

1. Open **Docker Desktop**
2. **Troubleshoot** → **Restart**
3. Or in Admin PowerShell: `Start-Service com.docker.service`
4. Wait 30–60s, run `docker version` again until **Server** shows a version

Then:

```powershell
cd "d:\7th Sem\DevOps\ResearchHub"

# free port 8000
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

docker compose up --build -d
docker compose ps
curl.exe http://localhost:8000/health
```

Migrations run **automatically** when the `api` container starts (`alembic upgrade head`).  
You do **not** need a separate `docker compose exec ... alembic` command.

URLs:
- API/UI: http://localhost:8000
- Gateway: http://localhost:8080
- Grafana: http://localhost:3001 (admin / admin)
- Prometheus: http://localhost:9090

Logs / stop:

```powershell
docker compose logs -f api
docker compose down
```

---

## 3. GitHub (PowerShell)

```powershell
git add .
git commit -m "Deploy ResearchOps AI"
git push origin main
```

Check Actions: **ResearchOps AI CI/CD Pipeline** is green.

---

## 4. Terraform → EC2 (PowerShell)

```powershell
aws configure
cd "d:\7th Sem\DevOps\ResearchHub\terraform"
copy terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
key_name = "YOUR_KEY"
```

```powershell
terraform init
terraform apply
terraform output public_ip
```

Save the IP as `EC2_IP`.

---

## 5. Ansible → deploy on EC2 (WSL)

```bash
cd "/mnt/d/7th Sem/DevOps/ResearchHub/ansible"
cp inventory.ini.example inventory.ini
```

Edit `inventory.ini`:

```ini
[research_server]
EC2_IP ansible_user=ubuntu ansible_ssh_private_key_file=PATH/TO/key.pem ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

```bash
chmod 400 PATH/TO/key.pem
ansible-playbook -i inventory.ini deploy.yml
curl http://EC2_IP/health
```

Open: `http://EC2_IP`

---

## 6. Cleanup (PowerShell)

```powershell
cd "d:\7th Sem\DevOps\ResearchHub\terraform"
terraform destroy
```

---

Full details: [deployment.md](deployment.md)

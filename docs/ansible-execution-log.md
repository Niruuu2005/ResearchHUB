# Ansible CLI Execution Log — ResearchLite Deployment

This document logs the exact Ansible CLI commands, configurations, and terminal execution outputs for provisioning, configuring, and deploying the **ResearchLite** microservice to the **AWS EC2** instance (`13.232.104.34`).

---

## 1. Directory Navigation & Key Permissions Setup

```bash
# Navigate to the ansible directory in WSL / Linux
cd "/mnt/d/7th Sem/DevOps/ResearchHub/ansible"

# Ensure SSH private key has strict 0400 permissions
mkdir -p ~/.ssh
cp /mnt/c/Users/npati/Downloads/research-hub-key-pair.pem ~/.ssh/research-hub-key-pair.pem
chmod 400 ~/.ssh/research-hub-key-pair.pem
```

---

## 2. Ansible Inventory Configuration (`inventory.ini`)

### File Content
```ini
[research_server]
13.232.104.34 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/research-hub-key-pair.pem ansible_ssh_common_args='-o StrictHostKeyChecking=no'
```

---

## 3. Connectivity Verification (`ansible ping`)

### Command
```bash
ansible all -i inventory.ini -m ping
```

### Terminal Output
```json
13.232.104.34 | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3"
    },
    "changed": false,
    "ping": "pong"
}
```

---

## 4. Playbook Execution (`ansible-playbook deploy.yml`)

### Command
```bash
ansible-playbook -i inventory.ini deploy.yml
```

### Terminal Output
```text
PLAY [Deploy ResearchLite Microservice on AWS EC2] **************************************************

TASK [Gathering Facts] ******************************************************************************
ok: [13.232.104.34]

TASK [Update apt package cache] *********************************************************************
changed: [13.232.104.34]

TASK [Install system dependencies and Git] **********************************************************
changed: [13.232.104.34]

TASK [Install Docker] *******************************************************************************
changed: [13.232.104.34]

TASK [Ensure Docker service is running and enabled] *************************************************
ok: [13.232.104.34]

TASK [Add ubuntu user to docker group] **************************************************************
changed: [13.232.104.34]

TASK [Create application deployment directory] ******************************************************
changed: [13.232.104.34]

TASK [Check if application repository already exists] ***********************************************
ok: [13.232.104.34]

TASK [Clone repository from GitHub] *****************************************************************
changed: [13.232.104.34]

TASK [Build Docker image for ResearchLite] **********************************************************
changed: [13.232.104.34]

TASK [Check if previous container exists] ***********************************************************
ok: [13.232.104.34]

TASK [Stop and remove old container if present] *****************************************************
skipping: [13.232.104.34]

TASK [Run new ResearchLite Docker container] ********************************************************
changed: [13.232.104.34]

TASK [Pause 5 seconds for application startup] ******************************************************
Pausing for 5 seconds
(ctrl+C then 'C' = continue early, ctrl+C then 'A' = abort)
ok: [13.232.104.34]

TASK [Verify application health endpoint] ***********************************************************
ok: [13.232.104.34]

TASK [Display deployment success message] ***********************************************************
ok: [13.232.104.34] => {
    "msg": "ResearchLite successfully deployed and operational! Healthcheck: {'service': 'ResearchLite', 'status': 'running', 'version': '1.0.0'}"
}

PLAY RECAP ******************************************************************************************
13.232.104.34              : ok=15   changed=11   unreachable=0    failed=0    skipped=1    rescued=0    ignored=0
```

---

## 5. Live Endpoint Verification

### Healthcheck Probe
```bash
curl http://13.232.104.34/health
```

**Output:**
```json
{
  "status": "running",
  "service": "ResearchLite",
  "version": "1.0.0"
}
```

### Research Endpoint Query
```bash
curl -X POST http://13.232.104.34/research \
     -H "Content-Type: application/json" \
     -d '{"topic": "DevOps"}'
```

**Output:**
```json
{
  "topic": "DevOps",
  "summary": "DevOps is the integration and automation of software development (Dev) and IT operations (Ops) to shorten the systems development life cycle and provide continuous delivery with high software quality.",
  "key_points": [
    "DevOps is the integration and automation of software development and IT operations.",
    "Shortens the systems development life cycle.",
    "Provides continuous delivery with high software quality."
  ],
  "papers": [
    {
      "title": "Continuous Delivery and DevOps: A Systematic Literature Review",
      "authors": ["Lianping Chen"],
      "year": 2018,
      "source": "OpenAlex",
      "url": "https://doi.org/10.1109/computer.2018.2888278",
      "doi": "10.1109/computer.2018.2888278"
    }
  ],
  "sources": [
    {
      "name": "Wikipedia",
      "title": "DevOps",
      "url": "https://en.wikipedia.org/wiki/DevOps"
    }
  ],
  "warnings": []
}
```

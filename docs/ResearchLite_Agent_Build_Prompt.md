# Coding Agent Prompt — Build ResearchLite DevOps FA Project

## Role

You are a senior Python + DevOps engineer responsible for **building the complete project files only** for an academic DevOps FA project named **ResearchLite**.

The student will perform **all operational and deployment steps manually**.

You must **NOT**:

- create AWS resources yourself
- run `terraform apply`
- run `terraform destroy`
- run Ansible against any server
- create or use AWS credentials
- create SSH keys
- push code to GitHub
- create GitHub repositories
- deploy anything automatically
- configure cloud accounts
- execute destructive commands
- hide deployment steps behind scripts

Your job is to generate a clean, complete, understandable codebase so that the student can manually demonstrate:

```text
GitHub → Terraform → AWS → Ansible → Docker → Research Microservice
```

The project must be simple enough for an academic FA but complete enough to demonstrate all required DevOps concepts.

---

# 1. Project Name

**ResearchLite**

### Full Title

**Automated Deployment of a Topic Research Microservice using GitHub, Terraform, AWS, Ansible, and Docker**

---

# 2. Core Goal

Build a small research microservice that accepts a topic and returns:

- a short topic summary
- important key points
- relevant academic papers
- source/reference links

The application itself should remain lightweight.

The main academic objective is to demonstrate:

- Git and GitHub
- Infrastructure as Code
- Terraform
- AWS EC2
- Ansible
- Docker
- containerized deployment
- manual DevOps workflow

---

# 3. Mandatory DevOps Flow

The project must be designed around exactly this sequence:

```text
Developer
   ↓
Git / GitHub
   ↓
Terraform
   ↓
AWS EC2
   ↓
Ansible
   ↓
Docker
   ↓
ResearchLite Microservice
   ↓
Browser / REST API
```

Use this responsibility mapping consistently:

```text
GitHub    = STORE
Terraform = CREATE
AWS       = HOST
Ansible   = CONFIGURE
Docker    = RUN
FastAPI   = SERVE
ResearchLite = RESEARCH
```

---

# 4. Important Manual-Execution Rule

The student wants to perform all commands manually during learning and demonstration.

Therefore:

## You MAY create

- application source code
- Dockerfile
- Terraform `.tf` files
- Ansible inventory template
- Ansible playbook
- requirements file
- tests
- documentation
- `.gitignore`
- example environment file
- manual deployment instructions

## You MUST NOT automate

- Git initialization
- Git commits
- GitHub creation
- AWS CLI configuration
- Terraform execution
- SSH key creation
- EC2 deployment
- Ansible execution
- Docker execution on EC2
- infrastructure cleanup

Do not create one-click deployment scripts such as:

```text
deploy.sh
setup_everything.sh
run_all.py
```

The purpose is for the student to understand and execute each DevOps stage manually.

---

# 5. Technology Stack

Use:

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API Framework | FastAPI |
| HTTP Client | httpx |
| Validation | Pydantic |
| Research Sources | Wikipedia API + OpenAlex API + Crossref API |
| ASGI Server | Uvicorn |
| Containerization | Docker |
| Infrastructure | Terraform |
| Cloud | AWS EC2 |
| Configuration Management | Ansible |
| Version Control | Git |
| Remote Repository | GitHub |
| Testing | pytest + FastAPI TestClient |

Do not introduce unnecessary technologies.

Do **not** add:

- Kubernetes
- Redis
- PostgreSQL
- Celery
- Kafka
- RabbitMQ
- vector databases
- authentication systems
- multi-agent frameworks
- LangChain
- LlamaIndex
- complex LLM orchestration

The project must stay suitable for an FA demonstration.

---

# 6. Functional Requirements

## 6.1 Health Check

Create:

```http
GET /health
```

Response:

```json
{
  "status": "running",
  "service": "ResearchLite"
}
```

---

## 6.2 Research Endpoint

Create:

```http
POST /research
```

Input:

```json
{
  "topic": "Quantum Computing"
}
```

Expected response structure:

```json
{
  "topic": "Quantum Computing",
  "summary": "...",
  "key_points": [
    "...",
    "...",
    "..."
  ],
  "papers": [
    {
      "title": "...",
      "authors": ["..."],
      "year": 2025,
      "source": "OpenAlex",
      "url": "..."
    }
  ],
  "sources": [
    {
      "name": "Wikipedia",
      "title": "...",
      "url": "..."
    }
  ],
  "warnings": []
}
```

---

## 6.3 Paper Search Endpoint

Create:

```http
GET /papers?topic=Quantum+Computing
```

Return relevant paper metadata using OpenAlex and/or Crossref.

---

# 7. Research Source Requirements

Create separate adapters/services for:

## Wikipedia

Use for:

- topic introduction
- summary/background
- source URL

Use the official/public Wikipedia API.

---

## OpenAlex

Use for:

- academic works
- paper titles
- publication year
- authors
- paper URL / DOI where available

Use public API access without requiring a key for the core project.

---

## Crossref

Use for:

- publication metadata
- DOI
- title
- author information
- publication year

Use public API access.

---

# 8. Research Processing Logic

Implement a simple deterministic research pipeline.

```text
Topic
  ↓
Validate Input
  ↓
Query Wikipedia
  ↓
Query OpenAlex
  ↓
Query Crossref
  ↓
Normalize Results
  ↓
Remove obvious duplicates
  ↓
Select most relevant papers
  ↓
Generate key points
  ↓
Return structured response
```

Do not build an autonomous research agent.

Do not claim the application performs fact verification unless such functionality is actually implemented.

---

# 9. Summary Strategy

Keep summarization simple and reliable.

For the mandatory version:

- use Wikipedia extract as the primary summary
- clean the text
- limit the summary to a reasonable length
- derive a few key points from retrieved text using lightweight deterministic logic

Do not require a paid LLM API.

If you include an optional LLM enhancement, isolate it clearly as optional and ensure the application works fully without it.

---

# 10. Reliability Requirements

The application must not completely fail if one research provider is unavailable.

For example:

```text
Wikipedia succeeds
OpenAlex succeeds
Crossref fails
```

The API should still return usable results with:

```json
{
  "warnings": [
    "Crossref service is temporarily unavailable."
  ]
}
```

Use:

- connection timeouts
- exception handling
- sensible HTTP status codes
- clear error messages

---

# 11. Input Validation

Research topic must:

- not be empty
- have a reasonable maximum length
- be stripped of leading/trailing whitespace

Return appropriate validation errors.

Do not execute user-provided data as code or shell commands.

---

# 12. Recommended Project Structure

Build exactly or very close to:

```text
researchlite/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── wikipedia_service.py
│   │   ├── openalex_service.py
│   │   ├── crossref_service.py
│   │   └── research_service.py
│   │
│   └── static/
│       └── index.html
│
├── terraform/
│   ├── versions.tf
│   ├── provider.tf
│   ├── variables.tf
│   ├── main.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
│
├── ansible/
│   ├── inventory.ini.example
│   └── deploy.yml
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   └── test_research.py
│
├── docs/
│   ├── architecture.md
│   ├── manual-deployment.md
│   └── viva.md
│
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── project.md
```

Keep the structure easy for a student to explain.

---

# 13. FastAPI Application Requirements

Create a clean FastAPI app.

`app/main.py` should:

- create the FastAPI instance
- include API routes
- expose Swagger docs at `/docs`
- provide the minimal frontend at `/` if practical

Suggested title:

```text
ResearchLite API
```

Suggested version:

```text
1.0.0
```

---

# 14. Frontend Requirement

Create a **very simple single-page HTML frontend**.

It should contain:

- project title
- topic input
- Research button
- loading text
- summary section
- key points
- papers
- sources
- error/warning display

Use only:

- HTML
- CSS
- vanilla JavaScript

Do not use React/Vue/Angular.

Keep it professional and minimal.

The frontend should call:

```http
POST /research
```

and render the returned JSON.

---

# 15. Docker Requirements

Create one root-level `Dockerfile`.

Use:

```dockerfile
FROM python:3.12-slim
```

The container must:

- install requirements
- copy application source
- expose port `8000`
- launch FastAPI using Uvicorn
- listen on `0.0.0.0`

Expected execution concept:

```bash
docker build -t researchlite .
docker run -d --name researchlite -p 80:8000 researchlite
```

Do not actually run these commands. Document them for the student.

---

# 16. Terraform Requirements

Terraform must create only the infrastructure necessary for the FA.

Use AWS.

Create:

1. AWS provider
2. one EC2 instance
3. one security group
4. necessary ingress rules
5. public IP output

Use an Ubuntu-compatible AMI approach.

Prefer a configurable AMI variable or use AWS data lookup where appropriate.

Variables should include at minimum:

- AWS region
- instance type
- key name
- project name
- allowed SSH CIDR

Default instance type should be inexpensive, such as:

```text
t2.micro
```

or an equivalent free-tier-compatible option where available.

Do not hardcode:

- access keys
- secret keys
- private keys

---

# 17. Terraform Security Group

Support:

## SSH

```text
TCP 22
```

Do not default SSH to the entire internet if avoidable.

Expose a variable:

```text
allowed_ssh_cidr
```

Explain that the student should set it to their public IP range where possible.

## Web Application

Expose:

```text
TCP 80
```

for browser access.

FastAPI port `8000` does not need to be publicly exposed if Docker maps:

```text
80:8000
```

---

# 18. Terraform Outputs

Provide useful outputs:

```text
instance_id
public_ip
application_url
```

Example conceptual result:

```text
application_url = http://XX.XX.XX.XX
```

---

# 19. Terraform Manual Commands

Document, but do not execute:

```bash
cd terraform
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

For cleanup:

```bash
terraform destroy
```

Explain each command in one short sentence.

---

# 20. Ansible Requirements

Create:

```text
ansible/deploy.yml
```

The playbook must configure the already-created EC2 instance.

Tasks should:

1. update apt package cache
2. install required prerequisites
3. install Docker
4. start/enable Docker
5. create project deployment directory
6. copy project files or clone the GitHub repository
7. build the Docker image
8. remove an old `researchlite` container if it exists
9. run the new container
10. expose application through host port 80
11. verify the `/health` endpoint

Keep the playbook readable.

Use Ansible modules where possible instead of raw shell commands.

---

# 21. GitHub Handling in Ansible

Since the student will create the GitHub repository manually, do not hardcode a repository URL.

Use an Ansible variable such as:

```yaml
repo_url: "YOUR_GITHUB_REPOSITORY_URL"
```

Clearly mark what the student must replace.

Alternatively, if using local copy deployment, document that approach cleanly.

Prefer GitHub clone/pull because it demonstrates the required GitHub → deployment connection.

---

# 22. Ansible Inventory Template

Create:

```text
ansible/inventory.ini.example
```

Example:

```ini
[research_server]
YOUR_EC2_PUBLIC_IP ansible_user=ubuntu ansible_ssh_private_key_file=../YOUR_KEY.pem
```

Do not include a real IP or key.

---

# 23. Ansible Manual Commands

Document but do not execute:

```bash
cp inventory.ini.example inventory.ini
```

Then edit the values manually.

Connectivity test:

```bash
ansible all -i inventory.ini -m ping
```

Deployment:

```bash
ansible-playbook -i inventory.ini deploy.yml
```

---

# 24. Git / GitHub Manual Workflow

Document exactly how the student performs Git manually.

Example:

```bash
git init
git add .
git commit -m "Initial ResearchLite project"
git branch -M main
git remote add origin <github-repository-url>
git push -u origin main
```

Also include a normal update cycle:

```bash
git add .
git commit -m "Update research service"
git push
```

Do not run or automate any of these.

---

# 25. `.gitignore`

Must include at least:

```gitignore
.env
*.pem
__pycache__/
.pytest_cache/
.venv/
venv/
.terraform/
*.tfstate
*.tfstate.*
terraform.tfvars
ansible/inventory.ini
```

Ensure no secret or generated infrastructure data is committed.

---

# 26. Tests

Create practical tests.

At minimum:

## `test_health.py`

Verify:

```http
GET /health
```

returns HTTP 200 and correct service status.

## `test_research.py`

Do not depend on live public APIs for every automated test.

Mock external source responses where sensible.

Test:

- valid topic
- empty/invalid topic
- partial source failure
- response schema

---

# 27. README Requirements

Create a clear `README.md` with these sections:

1. Project title
2. Overview
3. Problem statement
4. Architecture
5. Technology stack
6. Features
7. Repository structure
8. Local setup
9. Docker setup
10. Terraform manual setup
11. AWS verification
12. Ansible manual deployment
13. Application testing
14. Git/GitHub workflow
15. Security notes
16. Cleanup
17. Faculty demonstration flow
18. Viva quick reference

Keep README usable by a student following it from top to bottom.

---

# 28. `project.md`

Create a detailed academic project document containing:

- problem statement
- motivation
- objectives
- DevOps flow
- application architecture
- infrastructure architecture
- individual technology roles
- deployment workflow
- API design
- testing strategy
- security
- expected output
- demonstration flow
- deliverables
- future scope
- conclusion

Use the central flow repeatedly and consistently:

```text
GitHub → Terraform → AWS → Ansible → Docker → Research Microservice
```

---

# 29. Architecture Documentation

Create `docs/architecture.md`.

Include Mermaid diagrams.

## DevOps Architecture

Use a diagram representing:

```text
Developer
  ↓
GitHub
  ↓
Terraform
  ↓
AWS EC2
  ↓
Ansible
  ↓
Docker
  ↓
ResearchLite
  ↓
User
```

## Application Architecture

Represent:

```text
User
 ↓
FastAPI
 ↓
Research Service
 ├─ Wikipedia
 ├─ OpenAlex
 └─ Crossref
 ↓
Normalizer
 ↓
Structured Response
```

Keep diagrams easy to explain in a viva.

---

# 30. Manual Deployment Guide

Create:

```text
docs/manual-deployment.md
```

This file is extremely important.

The student must manually perform every major stage.

Structure it as:

## Phase 1 — Local Application

Commands to:

- create venv
- install requirements
- run FastAPI
- test `/health`
- test `/docs`

## Phase 2 — GitHub

Commands to:

- initialize Git
- commit
- create remote manually
- push

## Phase 3 — AWS Preparation

Explain:

- AWS account
- IAM/credentials requirement
- EC2 key pair creation
- safe storage of `.pem`

Do not automate key creation.

## Phase 4 — Terraform

Commands:

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

Explain what the student should observe after each command.

## Phase 5 — Verify AWS

Explain checking:

- EC2 running
- public IPv4
- security group

## Phase 6 — Ansible

Explain:

- inventory setup
- SSH key permissions
- `ansible -m ping`
- playbook run

## Phase 7 — Docker Verification

Explain SSHing into EC2 and manually running:

```bash
docker images
docker ps
```

only as verification.

## Phase 8 — Application Verification

Open:

```text
http://EC2_PUBLIC_IP
```

Then:

```text
http://EC2_PUBLIC_IP/health
```

and:

```text
http://EC2_PUBLIC_IP/docs
```

## Phase 9 — Cleanup

Manually run:

```bash
terraform destroy
```

---

# 31. Viva Notes

Create:

```text
docs/viva.md
```

Include short answers for:

- What is DevOps?
- What is the CAMS model?
- What is Git?
- Git vs GitHub?
- What is version control?
- What is Infrastructure as Code?
- Why Terraform?
- What is declarative infrastructure?
- Why AWS EC2?
- What is Ansible?
- Terraform vs Ansible?
- What is Docker?
- Image vs container?
- Why containerization?
- Why FastAPI?
- What is a microservice?
- Why use a microservice here?
- How does the complete deployment flow work?
- Why should `.pem` not be pushed to GitHub?
- Why should Terraform state be protected?
- What does port 22 do?
- What does port 80 do?
- How do you destroy infrastructure?
- What happens if Crossref/OpenAlex is unavailable?

End with:

```text
GitHub = STORE
Terraform = CREATE
AWS = HOST
Ansible = CONFIGURE
Docker = RUN
```

---

# 32. Code Quality Requirements

The code should be:

- small
- readable
- modular
- typed where useful
- well-named
- easy for a final-year student to explain
- free from unnecessary abstractions

Avoid enterprise architecture for a small FA.

Do not add 20 layers just to make the repository look larger.

---

# 33. Error Handling

Use clear errors.

Examples:

### Empty topic

```json
{
  "detail": "Topic must not be empty."
}
```

### Research Provider Error

Do not crash the entire request.

Return successful sources plus warnings.

---

# 34. API Timeouts

External HTTP requests must have finite timeouts.

Do not allow requests to wait indefinitely.

---

# 35. Environment Configuration

If configuration is required, provide:

```text
.env.example
```

The mandatory version should preferably require no external API keys.

Do not include secrets.

---

# 36. Local Development Instructions

Document:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

# 37. Docker Local Test

Document:

```bash
docker build -t researchlite .
docker run --rm -p 8000:8000 researchlite
```

Then open:

```text
http://localhost:8000
http://localhost:8000/health
http://localhost:8000/docs
```

The student performs these commands manually.

---

# 38. AWS Cost Awareness

Mention clearly in the documentation:

- EC2 may incur charges depending on account/free-tier status.
- Resources should be destroyed after demonstration.
- Never leave unnecessary instances running.

Do not make cost guarantees.

---

# 39. Acceptance Criteria

Before declaring the project complete, verify the repository contains all required files and logically satisfies:

### Application

- [ ] FastAPI starts successfully
- [ ] `/health` works
- [ ] `/research` exists
- [ ] `/papers` exists
- [ ] Wikipedia adapter exists
- [ ] OpenAlex adapter exists
- [ ] Crossref adapter exists
- [ ] partial provider failure is handled
- [ ] basic frontend works

### Docker

- [ ] valid Dockerfile
- [ ] application listens on `0.0.0.0:8000`
- [ ] container can expose service

### Terraform

- [ ] provider configuration
- [ ] EC2 resource
- [ ] security group
- [ ] SSH rule
- [ ] HTTP rule
- [ ] public IP output
- [ ] no secrets hardcoded

### Ansible

- [ ] inventory example
- [ ] Docker installation
- [ ] project deployment
- [ ] Docker build
- [ ] container start
- [ ] health verification

### Git

- [ ] `.gitignore`
- [ ] manual Git instructions
- [ ] no credentials/secrets

### Documentation

- [ ] README
- [ ] project.md
- [ ] architecture.md
- [ ] manual-deployment.md
- [ ] viva.md

---

# 40. Final Verification Approach

Before finishing your work:

1. Inspect the full repository tree.
2. Check imports and file paths.
3. Check Terraform references and variable names.
4. Check Ansible YAML syntax logically.
5. Check Docker paths.
6. Check README commands match actual file locations.
7. Check API endpoint names are consistent across code and documentation.
8. Check no secret values are present.
9. Check no automation bypasses the student's manual DevOps execution.
10. Run only **safe local development tests** if your environment allows it.

Do not provision or contact AWS infrastructure.

---

# 41. Expected Final Agent Response

When finished, report:

## Files Created

Show the complete repository tree.

## Application

State which endpoints exist.

## DevOps Components

State what was prepared for:

- GitHub
- Terraform
- AWS
- Ansible
- Docker

## Manual Steps Remaining for Student

Explicitly state that the student still needs to manually:

1. create/configure their GitHub repository
2. configure AWS credentials
3. create/select the EC2 SSH key pair
4. fill Terraform variables
5. run Terraform
6. configure Ansible inventory with EC2 IP/key
7. run Ansible
8. inspect Docker container
9. test the public application
10. run Terraform destroy after evaluation

Do not pretend these stages were completed.

---

# 42. Definition of Done

The project is finished only when the repository is a coherent, ready-to-use educational codebase where the student can personally execute the following process:

```text
1. Develop/Test locally
        ↓
2. Git commit + GitHub push
        ↓
3. terraform init
        ↓
4. terraform validate
        ↓
5. terraform plan
        ↓
6. terraform apply
        ↓
7. Verify AWS EC2
        ↓
8. Configure Ansible inventory
        ↓
9. ansible ping
        ↓
10. ansible-playbook deploy.yml
        ↓
11. Verify docker ps
        ↓
12. Open ResearchLite in browser
        ↓
13. Demonstrate research request
        ↓
14. terraform destroy
```

The student must be able to explain what happens at every step.

---

# Final Instruction to the Coding Agent

**Now build the complete ResearchLite repository according to this specification.**

Prioritize:

1. correctness
2. simplicity
3. manual learnability
4. clear separation of responsibilities
5. easy faculty demonstration

Do not over-engineer.

Do not perform cloud deployment.

Do not replace manual learning steps with automation.

Build the project files, documentation, templates, tests, and configuration needed so the student can manually perform and understand:

```text
GitHub → Terraform → AWS → Ansible → Docker → Research Microservice
```

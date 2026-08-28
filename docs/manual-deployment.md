# ResearchLite — Manual DevOps Deployment Guide

> **Academic FA Demonstration Guide**  
> Complete step-by-step walkthrough of the entire DevOps lifecycle:  
> **GitHub → Terraform → AWS EC2 → Ansible → Docker → Research Microservice**

---

## DevOps Responsibility Matrix

| Stage | Tool / Platform | Core Responsibility |
|---|---|---|
| **Phase 1 & 2** | **GitHub** | **STORE & TRACK**: Remote source code, CI tests, and revision history |
| **Phase 3 & 4** | **Terraform** | **CREATE**: Infrastructure as Code for AWS EC2 and Security Groups |
| **Phase 5** | **AWS EC2** | **HOST**: Cloud virtual machine hosting the runtime environment |
| **Phase 6** | **Ansible** | **CONFIGURE**: Configuration management, Docker installation, and app deployment |
| **Phase 7** | **Docker** | **RUN**: Isolated container running FastAPI on port 8000 (mapped to port 80) |
| **Phase 8** | **FastAPI Microservice** | **SERVE & RESEARCH**: Provides topic research summaries and literature search |
| **Phase 9** | **Terraform Cleanup** | **DESTROY**: Teardown cloud resources to avoid unexpected AWS charges |

---

## Phase 1 — Local Verification & Testing

Verify that the microservice runs and passes all automated tests on your local machine before cloud deployment.

1. **Activate your Python environment and run tests:**
   ```powershell
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   python -m pytest tests/ -v
   ```
   *Expected Output: All 12 tests pass (`12 passed in ...s`).*

2. **Test local server startup:**
   ```powershell
   uvicorn app.main:app --port 8000
   ```
   *Open [http://localhost:8000](http://localhost:8000) in your browser.*

---

## Phase 2 — GitHub Repository Setup

Your code and CI pipeline are stored in GitHub: `https://github.com/Niruuu2005/ResearchHUB.git`.

1. **Verify your Git status:**
   ```powershell
   git status
   ```

2. **Verify GitHub Actions CI:**
   - Open your repository on GitHub: `https://github.com/Niruuu2005/ResearchHUB/actions`
   - Confirm that the `ResearchLite CI` workflow runs and passes.

---

## Phase 3 — AWS Preparation (Prerequisites)

Before running Terraform, ensure you have your AWS account credentials and EC2 SSH Key Pair ready.

1. **Configure AWS CLI credentials on your local computer:**
   ```powershell
   aws configure
   ```
   *Provide your AWS Access Key ID, Secret Access Key, and default region (e.g., `ap-south-1` or `us-east-1`).*

2. **Create an EC2 Key Pair:**
   - Go to **AWS Console** → **EC2** → **Key Pairs** → **Create key pair**.
   - Name: `researchlite-key` (or your preferred name).
   - Type: `RSA`, format: `.pem`.
   - Download the `.pem` file and save it in a secure location (e.g., `C:\Users\<user>\.ssh\researchlite-key.pem`).
   - **Crucial**: Never commit the `.pem` file to GitHub!

---

## Phase 4 — Infrastructure as Code with Terraform

Navigate into the `terraform/` directory to create the AWS EC2 instance and Security Group.

1. **Move to the terraform folder:**
   ```powershell
   cd terraform
   ```

2. **Create your `terraform.tfvars` file:**
   Copy `terraform.tfvars.example` to `terraform.tfvars`:
   ```powershell
   cp terraform.tfvars.example terraform.tfvars
   ```
   Edit `terraform.tfvars` with your key name and preferred region:
   ```hcl
   aws_region       = "ap-south-1"
   instance_type    = "t2.micro"
   key_name         = "researchlite-key"   # Exact name of your AWS Key Pair
   allowed_ssh_cidr = "0.0.0.0/0"
   ```

3. **Initialize Terraform plugins:**
   ```powershell
   terraform init
   ```
   *What happens:* Downloads the HashiCorp AWS provider plugin.

4. **Validate configuration syntax:**
   ```powershell
   terraform validate
   ```
   *Expected Output: `Success! The configuration is valid.`*

5. **Generate an execution plan:**
   ```powershell
   terraform plan
   ```
   *What happens:* Terraform compares current state (none) with desired state (1 EC2 instance + 1 Security Group) and shows `Plan: 2 to add, 0 to change, 0 to destroy`.

6. **Apply and provision resources on AWS:**
   ```powershell
   terraform apply
   ```
   *Type `yes` when prompted.*

7. **Record Terraform Outputs:**
   Terraform will display output values upon completion:
   ```text
   Outputs:
   application_url = "http://13.233.xx.xx"
   instance_id     = "i-0abcd1234ef56789"
   public_ip       = "13.233.xx.xx"
   ```
   **Copy the `public_ip`** for the next step.

---

## Phase 5 — AWS EC2 Verification

Verify that the instance is running in the cloud.

1. In the **AWS EC2 Console**, inspect your instance named `ResearchLite-Server`.
2. Check that the Security Group (`ResearchLite-SecurityGroup`) has inbound rules for:
   - **Port 22 (SSH)**
   - **Port 80 (HTTP)**

---

## Phase 6 — Configuration Management with Ansible

Ansible will connect to your new EC2 instance over SSH, install Docker, pull the code from GitHub, build the image, and launch the container.

1. **Navigate to the ansible folder:**
   ```powershell
   cd ..\ansible
   ```

2. **Create and edit `inventory.ini`:**
   Copy `inventory.ini.example` to `inventory.ini`:
   ```powershell
   cp inventory.ini.example inventory.ini
   ```
   Edit `inventory.ini` with your EC2 Public IP and the path to your `.pem` key:
   ```ini
   [research_server]
   13.233.xx.xx ansible_user=ubuntu ansible_ssh_private_key_file="C:/path/to/researchlite-key.pem" ansible_ssh_common_args='-o StrictHostKeyChecking=no'
   ```

3. **Test SSH connectivity with Ansible Ping:**
   ```bash
   ansible all -i inventory.ini -m ping
   ```
   *Expected Output:*
   ```json
   13.233.xx.xx | SUCCESS => {
       "changed": false,
       "ping": "pong"
   }
   ```

4. **Execute the deployment playbook:**
   ```bash
   ansible-playbook -i inventory.ini deploy.yml
   ```
   *What Ansible does automatically:*
   - Updates apt cache on Ubuntu.
   - Installs Docker CE and Git.
   - Clones `https://github.com/Niruuu2005/ResearchHUB.git` into `/opt/researchhub`.
   - Runs `docker build` inside the EC2 server.
   - Starts the Docker container mapped to port 80.
   - Verifies the `/health` endpoint.

---

## Phase 7 — Docker Verification on EC2

To demonstrate Docker container execution to your evaluator:

1. **SSH into the EC2 instance:**
   ```bash
   ssh -i /path/to/researchlite-key.pem ubuntu@13.233.xx.xx
   ```

2. **Inspect Docker images and running containers:**
   ```bash
   docker images
   docker ps
   ```
   *You will see `researchlite:latest` running with `0.0.0.0:80->8000/tcp`.*

3. **Inspect container logs:**
   ```bash
   docker logs researchlite
   ```

---

## Phase 8 — Live Application Demonstration

1. Open your browser and navigate to:
   ```text
   http://YOUR_EC2_PUBLIC_IP
   ```
2. **Demonstrate features:**
   - Enter topic query: `Quantum Computing` or `DevOps`.
   - Review the synthesized topic summary.
   - Inspect the extracted key takeaways.
   - Click on academic paper titles and DOI links.
   - Open the Swagger API docs at `http://YOUR_EC2_PUBLIC_IP/docs`.
   - Show the healthcheck at `http://YOUR_EC2_PUBLIC_IP/health`.

---

## Phase 9 — Infrastructure Teardown (Cleanup)

To prevent ongoing AWS EC2 charges after your assessment, destroy the infrastructure:

1. Navigate back to the `terraform/` directory:
   ```powershell
   cd ..\terraform
   ```

2. Run Terraform destroy:
   ```powershell
   terraform destroy
   ```
3. Type `yes` to confirm. Terraform will terminate the EC2 instance and delete the security group.

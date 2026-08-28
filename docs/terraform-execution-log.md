# Terraform CLI Execution Log — ResearchLite Infrastructure

This document logs the exact Terraform CLI commands, configurations, and terminal execution outputs for provisioning the **ResearchLite** cloud infrastructure on **AWS EC2**.

---

## 1. Directory Navigation

```powershell
PS D:\7th Sem\DevOps\ResearchHub> cd terraform
PS D:\7th Sem\DevOps\ResearchHub\terraform>
```

---

## 2. Terraform Initialization (`terraform init`)

### Command
```powershell
terraform init
```

### Terminal Output
```text
Initializing the backend...

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.65.0...
- Installed hashicorp/aws v5.65.0 (signed by HashiCorp)

Terraform has created a lock file .terraform.lock.hcl to record the provider
selections it made above. Include this file in your version control repository
so that Terraform can guarantee to make the same selections by default when
you run "terraform init" in the future.

Terraform has been successfully initialized!

You may now begin working with Terraform. Try running "terraform plan" to see
any changes that are required for your infrastructure. All Terraform commands
should now work.

If you ever set or change modules or backend configuration for Terraform,
rerun this command to reinitialize your working directory. If you forget, other
commands will detect it and remind you to do so if necessary.
```

---

## 3. Configuration Validation (`terraform validate`)

### Command
```powershell
terraform validate
```

### Terminal Output
```text
Success! The configuration is valid.
```

---

## 4. Execution Plan Generation (`terraform plan`)

### Command
```powershell
terraform plan
```

### Terminal Output
```text
data.aws_ami.ubuntu: Reading...
data.aws_ami.ubuntu: Read complete after 1s [id=ami-002a6ae76416021fe]

Terraform used the selected providers to generate the following execution plan.
Resource actions are indicated with the following symbols:
  + create

Terraform will perform the following actions:

  # aws_security_group.researchlite_sg will be created
  + resource "aws_security_group" "researchlite_sg" {
      + arn                    = (known after apply)
      + description            = "Security group for ResearchLite microservice allowing SSH (22) and HTTP (80)"
      + egress                 = [
          + {
              + cidr_blocks      = [
                  + "0.0.0.0/0",
                ]
              + description      = "Allow all outbound internet traffic"
              + from_port        = 0
              + ipv6_cidr_blocks = []
              + prefix_list_ids  = []
              + protocol         = "-1"
              + security_groups  = []
              + self             = false
              + to_port          = 0
            },
        ]
      + id                     = (known after apply)
      + ingress                = [
          + {
              + cidr_blocks      = [
                  + "0.0.0.0/0",
                ]
              + description      = "Public HTTP web traffic"
              + from_port        = 80
              + ipv6_cidr_blocks = []
              + prefix_list_ids  = []
              + protocol         = "tcp"
              + security_groups  = []
              + self             = false
              + to_port          = 80
            },
          + {
              + cidr_blocks      = [
                  + "0.0.0.0/0",
                ]
              + description      = "SSH administrative access"
              + from_port        = 22
              + ipv6_cidr_blocks = []
              + prefix_list_ids  = []
              + protocol         = "tcp"
              + security_groups  = []
              + self             = false
              + to_port          = 22
            },
        ]
      + name                   = "ResearchLite-SecurityGroup"
      + name_prefix            = (known after apply)
      + owner_id               = (known after apply)
      + revoke_rules_on_delete = false
      + tags                   = {
          + "Name" = "ResearchLite-SG"
        }
      + tags_all               = {
          + "Environment" = "Development"
          + "ManagedBy"   = "Terraform"
          + "Name"        = "ResearchLite-SG"
          + "Project"     = "ResearchLite"
        }
      + vpc_id                 = (known after apply)
    }

  # aws_instance.researchlite_ec2 will be created
  + resource "aws_instance" "researchlite_ec2" {
      + ami                                  = "ami-002a6ae76416021fe"
      + arn                                  = (known after apply)
      + associate_public_ip_address          = (known after apply)
      + availability_zone                    = (known after apply)
      + cpu_core_count                       = (known after apply)
      + cpu_threads_per_core                 = (known after apply)
      + disable_api_stop                     = (known after apply)
      + disable_api_termination              = (known after apply)
      + ebs_optimized                        = (known after apply)
      + get_password_data                    = false
      + id                                   = (known after apply)
      + instance_type                        = "t3.micro"
      + key_name                             = "research-hub-key-pair"
      + monitoring                           = (known after apply)
      + private_ip                           = (known after apply)
      + public_ip                            = (known after apply)
      + source_dest_check                    = true
      + subnet_id                            = (known after apply)
      + tags                                 = {
          + "Name" = "ResearchLite-Server"
        }
      + tags_all                             = {
          + "Environment" = "Development"
          + "ManagedBy"   = "Terraform"
          + "Name"        = "ResearchLite-Server"
          + "Project"     = "ResearchLite"
        }
      + vpc_security_group_ids               = (known after apply)

      + root_block_device {
          + delete_on_termination = true
          + device_name           = (known after apply)
          + encrypted             = (known after apply)
          + iops                  = (known after apply)
          + volume_size           = 10
          + volume_type           = "gp3"
        }
    }

Plan: 2 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + application_url = (known after apply)
  + instance_id     = (known after apply)
  + public_ip       = (known after apply)
```

---

## 5. Infrastructure Provisioning (`terraform apply`)

### Command
```powershell
terraform apply
```

### Interactive Confirmation
```text
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

### Terminal Output
```text
aws_security_group.researchlite_sg: Creating...
aws_security_group.researchlite_sg: Creation complete after 2s [id=sg-010856ed2eb9a158d]
aws_instance.researchlite_ec2: Creating...
aws_instance.researchlite_ec2: Still creating... [00m10s elapsed]
aws_instance.researchlite_ec2: Creation complete after 13s [id=i-079469f22e28a78ad]

Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:

application_url = "http://13.232.104.34"
instance_id = "i-079469f22e28a78ad"
public_ip = "13.232.104.34"
```

---

## 6. Infrastructure Teardown (`terraform destroy`)

### Command
```powershell
terraform destroy
```

### Interactive Confirmation & Output
```text
aws_security_group.researchlite_sg: Refreshing state... [id=sg-010856ed2eb9a158d]
aws_instance.researchlite_ec2: Refreshing state... [id=i-079469f22e28a78ad]

Terraform will perform the following actions:

  # aws_instance.researchlite_ec2 will be destroyed
  - resource "aws_instance" "researchlite_ec2" {
      - id                   = "i-079469f22e28a78ad"
      - tags                 = {
          - "Name" = "ResearchLite-Server"
        }
      ...
    }

  # aws_security_group.researchlite_sg will be destroyed
  - resource "aws_security_group" "researchlite_sg" {
      - id   = "sg-010856ed2eb9a158d"
      ...
    }

Plan: 0 to add, 0 to change, 2 to destroy.

Do you want to destroy all resources?
  Terraform will totally destroy all the resources managed by this configuration.
  Only 'yes' will be accepted to confirm.

  Enter a value: yes

aws_instance.researchlite_ec2: Destroying... [id=i-079469f22e28a78ad]
aws_instance.researchlite_ec2: Still destroying... [00m10s elapsed]
aws_instance.researchlite_ec2: Destruction complete after 30s
aws_security_group.researchlite_sg: Destroying... [id=sg-010856ed2eb9a158d]
aws_security_group.researchlite_sg: Destruction complete after 2s

Destroy complete! Resources: 2 destroyed.
```

variable "aws_region" {
  type        = string
  description = "AWS region for provisioning resources"
  default     = "ap-south-1"
}

variable "project_name" {
  type        = string
  description = "Name identifier for the project resources"
  default     = "ResearchLite"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance size (Free Tier eligible: t2.micro or t3.micro)"
  default     = "t2.micro"
}

variable "key_name" {
  type        = string
  description = "Name of the pre-existing AWS EC2 Key Pair for SSH access"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "CIDR block allowed to connect over SSH (port 22). Set to your public IP (e.g., 203.0.113.4/32) or 0.0.0.0/0 for testing."
  default     = "0.0.0.0/0"
}

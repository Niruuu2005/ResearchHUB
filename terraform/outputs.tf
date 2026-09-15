output "instance_id" {
  description = "The AWS EC2 Instance ID"
  value       = aws_instance.researchops_ec2.id
}

output "public_ip" {
  description = "The Public IPv4 Address of the EC2 Instance"
  value       = aws_instance.researchops_ec2.public_ip
}

output "application_url" {
  description = "Direct browser URL to access the deployed ResearchOps AI platform (via Gateway)"
  value       = "http://${aws_instance.researchops_ec2.public_ip}"
}

output "api_url" {
  description = "Direct browser URL to access the FastAPI backend directly"
  value       = "http://${aws_instance.researchops_ec2.public_ip}:8000"
}

output "grafana_url" {
  description = "Direct browser URL to access the Grafana Observability Dashboard"
  value       = "http://${aws_instance.researchops_ec2.public_ip}:3001"
}

output "prometheus_url" {
  description = "Direct browser URL to access the Prometheus Metrics Dashboard"
  value       = "http://${aws_instance.researchops_ec2.public_ip}:9090"
}

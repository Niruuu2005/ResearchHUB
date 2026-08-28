output "instance_id" {
  description = "The AWS EC2 Instance ID"
  value       = aws_instance.researchlite_ec2.id
}

output "public_ip" {
  description = "The Public IPv4 Address of the EC2 Instance"
  value       = aws_instance.researchlite_ec2.public_ip
}

output "application_url" {
  description = "Direct browser URL to access the deployed ResearchLite application"
  value       = "http://${aws_instance.researchlite_ec2.public_ip}"
}

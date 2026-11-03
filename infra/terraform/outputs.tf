output "public_ip" {
  description = "Point your DuckDNS name at this address."
  value       = aws_eip.app.public_ip
}

output "instance_id" {
  description = "Save as the GitHub variable AWS_INSTANCE_ID."
  value       = aws_instance.app.id
}

output "deploy_role_arn" {
  description = "Save as the GitHub variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.deploy.arn
}

output "bucket_name" {
  description = "Save as the GitHub variable S3_BUCKET, and as S3_BUCKET in Parameter Store."
  value       = aws_s3_bucket.main.id
}

output "parameter_path" {
  description = "Parameter Store folder for production settings."
  value       = var.parameter_path
}

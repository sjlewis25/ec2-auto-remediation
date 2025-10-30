output "dev_instance_id" {
  value = aws_instance.dev.id
}

output "prod_instance_id" {
  value = aws_instance.prod.id
}

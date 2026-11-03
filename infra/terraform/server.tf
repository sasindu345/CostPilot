# One small server runs everything except Qdrant, which uses Qdrant Cloud.
# There is no SSH port. You reach the server through AWS Systems Manager instead.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

# The latest Amazon Linux 2023, looked up from AWS rather than written down.
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-*-x86_64"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_security_group" "web" {
  name        = "${var.project_name}-web"
  description = "HTTP and HTTPS in, anything out"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "web" {
  #checkov:skip=CKV_AWS_260:Port 80 must be public so Let's Encrypt can check the domain. Caddy redirects it to HTTPS
  for_each = {
    http-ipv4  = { port = 80, cidr_ipv4 = "0.0.0.0/0", cidr_ipv6 = null }
    https-ipv4 = { port = 443, cidr_ipv4 = "0.0.0.0/0", cidr_ipv6 = null }
    http-ipv6  = { port = 80, cidr_ipv4 = null, cidr_ipv6 = "::/0" }
    https-ipv6 = { port = 443, cidr_ipv4 = null, cidr_ipv6 = "::/0" }
  }
  security_group_id = aws_security_group.web.id
  description       = "Public ${each.key}. Caddy turns HTTP into HTTPS"
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
  cidr_ipv4         = each.value.cidr_ipv4
  cidr_ipv6         = each.value.cidr_ipv6
}

# The server must reach GitHub, Gemini, Qdrant Cloud, AWS and Let's Encrypt.
resource "aws_vpc_security_group_egress_rule" "all" {
  for_each = {
    ipv4 = { cidr_ipv4 = "0.0.0.0/0", cidr_ipv6 = null }
    ipv6 = { cidr_ipv4 = null, cidr_ipv6 = "::/0" }
  }
  security_group_id = aws_security_group.web.id
  description       = "Outgoing ${each.key}"
  ip_protocol       = "-1"
  cidr_ipv4         = each.value.cidr_ipv4
  cidr_ipv6         = each.value.cidr_ipv6
}

resource "aws_instance" "app" {
  #checkov:skip=CKV_AWS_126:Detailed monitoring costs money. Basic 5-minute monitoring is free
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  ebs_optimized          = true
  monitoring             = false

  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    swap_gb = var.swap_gb
  })

  # Only the newer, safer way to read instance details is allowed.
  # A limit of 2 lets the app inside Docker get its S3 permissions, as AWS advises for containers.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_gb
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name = var.project_name
  }

  # A newer Amazon Linux image must not replace a running server by surprise.
  lifecycle {
    ignore_changes = [ami, user_data]
  }
}

# A fixed address, so the DuckDNS name never needs changing.
# A public IPv4 address costs about $3.65 a month, taken from free credits.
resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id
}

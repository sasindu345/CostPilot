mock_provider "aws" {}

override_data {
  target = data.aws_iam_policy_document.server_trust
  values = { json = jsonencode({ Version = "2012-10-17", Statement = [] }) }
}

override_data {
  target = data.aws_iam_policy_document.server
  values = { json = jsonencode({ Version = "2012-10-17", Statement = [] }) }
}

override_data {
  target = data.aws_iam_policy_document.deploy_trust
  values = { json = jsonencode({ Version = "2012-10-17", Statement = [] }) }
}

override_data {
  target = data.aws_iam_policy_document.deploy
  values = { json = jsonencode({ Version = "2012-10-17", Statement = [] }) }
}

override_data {
  target = data.aws_iam_policy_document.bucket
  values = { json = jsonencode({ Version = "2012-10-17", Statement = [] }) }
}

override_data {
  target = data.aws_subnets.default
  values = { ids = ["subnet-test"] }
}

run "deploy_role_trusts_immutable_github_subject" {
  command = plan

  variables {
    aws_region           = "ap-south-1"
    bucket_name          = "example-bucket"
    github_repository    = "example-owner/example-repo"
    github_owner_id      = "123"
    github_repository_id = "456"
    github_environment   = "production"
    alert_email          = "example@example.com"
    create_budget        = false
  }

  assert {
    condition     = local.github_oidc_subject == "repo:example-owner@123/example-repo@456:environment:production"
    error_message = "The deploy role must trust GitHub's immutable repository subject in the production environment."
  }
}

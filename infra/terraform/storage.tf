# One private bucket, with a folder for each job:
#   uploads/  bill files, written by the app
#   backups/  nightly database backups
#   deploy/   the files each deployment needs
resource "aws_s3_bucket" "main" {
  #checkov:skip=CKV_AWS_145:S3's own AES-256 encryption is used. A KMS key costs $1 a month. See decision 0004
  #checkov:skip=CKV_AWS_18:Access logs need a second bucket. Not worth it while there is one user
  #checkov:skip=CKV_AWS_144:Copying to a second region doubles the cost. Versioning and nightly backups cover mistakes
  #checkov:skip=CKV2_AWS_62:Nothing needs to react to new files
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket                  = aws_s3_bucket.main.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# S3's own AES-256 encryption is free. A customer KMS key costs $1 a month. See decision 0004.
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Keeps overwritten or deleted files for a few days, so a mistake can be undone.
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket     = aws_s3_bucket.main.id
  depends_on = [aws_s3_bucket_versioning.main]

  rule {
    id     = "expire-backups"
    status = "Enabled"
    filter {
      prefix = "backups/"
    }
    expiration {
      days = var.backup_keep_days
    }
  }

  rule {
    id     = "expire-deploy-bundles"
    status = "Enabled"
    filter {
      prefix = "deploy/"
    }
    expiration {
      days = var.deploy_bundle_keep_days
    }
  }

  rule {
    id     = "tidy-up"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = var.old_version_keep_days
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Refuse any request that is not encrypted in transit.
data "aws_iam_policy_document" "bucket" {
  statement {
    sid       = "HttpsOnly"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.main.arn, "${aws_s3_bucket.main.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "main" {
  bucket     = aws_s3_bucket.main.id
  policy     = data.aws_iam_policy_document.bucket.json
  depends_on = [aws_s3_bucket_public_access_block.main]
}

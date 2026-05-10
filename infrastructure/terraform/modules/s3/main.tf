resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  bucket_name = coalesce(
    var.bucket_name,
    "${var.project_name}-${var.environment}-handwriting-images-${random_id.bucket_suffix.hex}",
  )
}

resource "aws_s3_bucket" "images" {
  bucket = local.bucket_name

  tags = merge(var.tags, {
    Name = local.bucket_name
  })
}

resource "aws_s3_bucket_public_access_block" "images" {
  bucket = aws_s3_bucket.images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    id     = "archive-handwriting-images"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }
}

data "aws_iam_policy_document" "tenant_scoped_s3_access" {
  statement {
    sid = "ListTenantPrefix"
    actions = [
      "s3:ListBucket",
    ]
    resources = [aws_s3_bucket.images.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["$${aws:PrincipalTag/tenant_id}/*"]
    }
  }

  statement {
    sid = "ReadWriteTenantPrefix"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.images.arn}/$${aws:PrincipalTag/tenant_id}/*",
    ]
  }
}

resource "aws_iam_policy" "tenant_scoped_s3_access" {
  name        = "${var.project_name}-${var.environment}-tenant-scoped-s3-access"
  description = "Allows TDSE pods to access only tenant-prefixed image objects."
  policy      = data.aws_iam_policy_document.tenant_scoped_s3_access.json

  tags = var.tags
}

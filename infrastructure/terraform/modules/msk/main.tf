resource "aws_kms_key" "msk" {
  description             = "KMS key for MSK encryption at rest"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-msk-kms"
  })
}

resource "aws_security_group" "msk" {
  name        = "${var.project_name}-${var.environment}-msk-sg"
  description = "Allow Kafka TLS traffic only from the EKS cluster."
  vpc_id      = var.vpc_id

  ingress {
    description     = "Kafka TLS from EKS"
    from_port       = 9094
    to_port         = 9094
    protocol        = "tcp"
    security_groups = [var.eks_cluster_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-msk-sg"
  })
}

resource "aws_msk_cluster" "this" {
  cluster_name           = "${var.project_name}-${var.environment}-msk"
  kafka_version          = var.kafka_version
  number_of_broker_nodes = 2

  broker_node_group_info {
    instance_type   = "kafka.t3.small"
    client_subnets  = var.private_subnet_ids
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = 100
      }
    }
  }

  client_authentication {
    unauthenticated = true
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.msk.arn

    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-msk"
  })
}

resource "null_resource" "topics" {
  for_each = var.create_topics ? toset(var.topics) : toset([])

  triggers = {
    topic             = each.key
    bootstrap_servers = aws_msk_cluster.this.bootstrap_brokers_tls
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      command -v kafka-topics.sh >/dev/null
      client_config="$(mktemp)"
      trap 'rm -f "$${client_config}"' EXIT
      printf 'security.protocol=SSL\n' > "$${client_config}"
      kafka-topics.sh \
        --bootstrap-server "${aws_msk_cluster.this.bootstrap_brokers_tls}" \
        --command-config "$${client_config}" \
        --create \
        --if-not-exists \
        --topic "${each.key}" \
        --replication-factor 2 \
        --partitions 3
    EOT
  }
}

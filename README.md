# AWS Infrastructure Runbook Generator

Um sistema automatizado para gerar documentação completa da infraestrutura AWS.

## 📋 Visão Geral

Este projeto automatiza a coleta de informações sobre recursos AWS e gera um runbook detalhado em formato Markdown e DOCX. É especialmente útil para:

- **Auditorias de infraestrutura**
- **Documentação para compliance**
- **Onboarding de novos membros da equipe**

## 🚀 Recursos

### Serviços AWS Suportados

- **EC2**: Instâncias, VPCs e Subnets
- **Lambda**: Funções e configurações
- **RDS**: Instâncias e clusters
- **API Gateway**: APIs REST
- **CloudFront**: Distribuições
- **ELB/ALB**: Load Balancers
- **ECS**: Clusters e serviços
- **SNS**: Tópicos
- **EventBridge**: Rules e eventos
- **AWS Backup**: Vaults
- **Organizations**: Informações da organização
- **IAM**: Usuários

## 📦 Pré-requisitos

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Python 3.8+
sudo apt-get update
sudo apt-get install python3 python3-pip

# jq (para processamento JSON)
sudo apt-get install jq

# Pandoc (para conversão DOCX)
sudo apt-get install pandoc

## ⚙️ Instalação e Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/ArthurSampaio13/runbook.git
cd runbook
```

### 2. Instale dependências Python

```bash
pip3 install -r requirements.txt
```

### Opção 3: Execução Direta do Python

```bash
# Para uma única conta/região
python3 runbook_orchestrator.py

# Com variáveis específicas
TARGET_ACCOUNTS=123456789012 REGIONS_TO_SCAN=us-east-1 python3 runbook_orchestrator.py
```

## 📊 Saída

O sistema gera os seguintes arquivos no diretório `output/`:

- **Markdown**: `aws_infrastructure_runbook_YYYYMMDD_HHMMSS.md`
- **DOCX**: `aws_infrastructure_runbook_YYYYMMDD_HHMMSS.docx`

### Exemplo de Estrutura do Runbook

```markdown
# AWS Infrastructure Runbook

**Organization Overview**
- **Total Accounts Scanned:** 3
- **Regions Scanned:** us-east-1, us-west-2
- **Generated:** 2024-01-15 14:30:00 UTC

## Account Information
| Field | Value |
|-------|-------|
| Account ID | 123456789012 |
| User ID | AIDACKCEVSQ6C2EXAMPLE |

## VPC Summary
| VPC ID | CIDR Block | State | Default |
|--------|------------|-------|---------|
| vpc-12345678 | 10.0.0.0/16 | available | false |

## EC2 Instances
| Instance ID | Name | Type | State | AZ | Launch Time |
|-------------|------|------|-------|----|-------------|
| i-1234567890abcdef0 | WebServer | t3.micro | running | us-east-1a | 2024-01-10T10:00:00Z |
```
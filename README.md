# AWS Infrastructure Runbook Generator

Um sistema automatizado para gerar documentação completa da infraestrutura AWS.

## 📋 Visão Geral

Este projeto automatiza a coleta de informações sobre recursos AWS e gera um runbook detalhado em formato Markdown e DOCX. É especialmente útil para:

- **Auditorias de infraestrutura**
- **Documentação para compliance**
- **Onboarding de novos membros da equipe**

## 🚀 Recursos

### Serviços AWS Suportados

- **EC2**: Instâncias, VPCs, Subnets, Security Groups
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

### Funcionalidades

- ✅ **Multi-conta**: Suporte completo para AWS Organizations
- ✅ **Multi-região**: Coleta dados de múltiplas regiões
- ✅ **Cross-account access**: Roles automatizados via Terraform
- ✅ **Formato profissional**: Saída em Markdown e DOCX
- ✅ **Tratamento de erros**: Robusto e confiável
- ✅ **Logs detalhados**: Para troubleshooting
- ✅ **Configuração flexível**: Via variáveis de ambiente

## 📦 Pré-requisitos

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Python 3.8+
sudo apt-get update
sudo apt-get install python3 python3-pip

# jq (para processamento JSON)
sudo apt-get install jq

# Pandoc (para conversão DOCX)
sudo apt-get install pandoc

# Terragrunt (opcional)
wget https://github.com/gruntwork-io/terragrunt/releases/download/v0.50.0/terragrunt_linux_amd64
sudo mv terragrunt_linux_amd64 /usr/local/bin/terragrunt
sudo chmod +x /usr/local/bin/terragrunt
```

### Permissões AWS

- TODO 

## ⚙️ Instalação e Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/aws-runbook-generator.git
cd aws-runbook-generator
```

### 2. Instale dependências Python

```bash
pip3 install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Exemplo de configuração:

```env
AWS_DEFAULT_REGION=us-east-1
TARGET_ACCOUNTS=123456789012,123456789013,123456789014
REGIONS_TO_SCAN=us-east-1,us-west-2,eu-west-1
CROSS_ACCOUNT_ROLE=RunbookGeneratorRole
MAX_WORKERS=5
```

## 🎯 Uso

### Opção 1: Execução Completa (Recomendado)

```bash
# Deploy da infraestrutura + Geração do runbook
./deploy.sh all
```

### Opção 2: Execução em Etapas

```bash
# 1. Setup do ambiente
./deploy.sh setup

# 2. Deploy dos cross-account roles
./deploy.sh deploy

# 3. Geração do runbook
./deploy.sh generate

# 4. Limpeza (opcional)
./deploy.sh cleanup
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
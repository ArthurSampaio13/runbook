#!/usr/bin/env python3
"""
AWS Runbook Generator
Gera automaticamente um documento Word (.docx) com inventário completo de recursos AWS
"""

import boto3
import json
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.shared import OxmlElement, qn
import logging
import sys
import os
from botocore.exceptions import ClientError, NoCredentialsError

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AWSRunbookGenerator:
    def __init__(self):
        self.session = None
        self.account_id = None
        self.account_name = None
        self.doc = Document()
        self.data = {}
        
    def setup_aws_session(self):
        """Configura a sessão AWS e obtém informações da conta"""
        try:
            self.session = boto3.Session()
            sts_client = self.session.client('sts')
            identity = sts_client.get_caller_identity()
            self.account_id = identity['Account']
            logger.info(f"Conectado à conta AWS: {self.account_id}")
            return True
        except NoCredentialsError:
            logger.error("Credenciais AWS não encontradas. Configure suas credenciais.")
            return False
        except Exception as e:
            logger.error(f"Erro ao conectar com AWS: {str(e)}")
            return False
    
    def collect_account_summary(self):
        """Coleta informações gerais da conta"""
        logger.info("Coletando informações da conta...")
        try:
            sts_client = self.session.client('sts')
            identity = sts_client.get_caller_identity()
            
            iam_client = self.session.client('iam')
            account_aliases = iam_client.list_account_aliases()
            
            self.data['account_summary'] = {
                'account_id': identity['Account'],
                'user_id': identity.get('UserId', 'N/A'),
                'arn': identity.get('Arn', 'N/A'),
                'aliases': account_aliases.get('AccountAliases', [])
            }
            
            if self.data['account_summary']['aliases']:
                self.account_name = self.data['account_summary']['aliases'][0]
            else:
                self.account_name = f"AWS-{self.account_id}"
                
        except Exception as e:
            logger.error(f"Erro ao coletar informações da conta: {str(e)}")
            self.data['account_summary'] = {'error': str(e)}
    
    def collect_organizations(self):
        """Coleta informações do AWS Organizations"""
        logger.info("Coletando informações do Organizations...")
        try:
            org_client = self.session.client('organizations')
            org_info = org_client.describe_organization()
            
            self.data['organizations'] = {
                'organization_id': org_info['Organization']['Id'],
                'master_account_id': org_info['Organization']['MasterAccountId'],
                'feature_set': org_info['Organization']['FeatureSet']
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWSOrganizationsNotInUseException':
                self.data['organizations'] = {'status': 'Não está em uma organização'}
            else:
                self.data['organizations'] = {'error': str(e)}
        except Exception as e:
            self.data['organizations'] = {'error': str(e)}
    
    def collect_control_tower(self):
        """Coleta informações do AWS Control Tower"""
        logger.info("Coletando informações do Control Tower...")
        try:
            ct_client = self.session.client('controltower')
            landing_zones = ct_client.list_landing_zones()
            
            self.data['control_tower'] = {
                'status': 'Ativo' if landing_zones['landingZones'] else 'Inativo',
                'landing_zones': len(landing_zones['landingZones'])
            }
        except Exception as e:
            self.data['control_tower'] = {'status': 'Não disponível', 'error': str(e)}
    
    def collect_vpc_summary(self):
        """Coleta informações de VPCs"""
        logger.info("Coletando informações de VPCs...")
        try:
            ec2_client = self.session.client('ec2')
            
            # VPCs
            vpcs = ec2_client.describe_vpcs()
            
            # Subnets
            subnets = ec2_client.describe_subnets()
            
            # VPC Peering
            peering = ec2_client.describe_vpc_peering_connections()
            
            self.data['vpc_summary'] = {
                'total_vpcs': len(vpcs['Vpcs']),
                'total_subnets': len(subnets['Subnets']),
                'peering_connections': len(peering['VpcPeeringConnections']),
                'vpcs': [
                    {
                        'vpc_id': vpc['VpcId'],
                        'cidr_block': vpc['CidrBlock'],
                        'state': vpc['State'],
                        'is_default': vpc.get('IsDefault', False)
                    } for vpc in vpcs['Vpcs']
                ]
            }
        except Exception as e:
            self.data['vpc_summary'] = {'error': str(e)}
    
    def collect_route53(self):
        """Coleta informações do Route 53"""
        logger.info("Coletando informações do Route 53...")
        try:
            route53_client = self.session.client('route53')
            hosted_zones = route53_client.list_hosted_zones()
            
            zones_data = []
            for zone in hosted_zones['HostedZones']:
                zone_info = {
                    'name': zone['Name'],
                    'id': zone['Id'],
                    'record_count': zone['ResourceRecordSetCount']
                }
                zones_data.append(zone_info)
            
            self.data['route53'] = {
                'total_zones': len(zones_data),
                'zones': zones_data
            }
        except Exception as e:
            self.data['route53'] = {'error': str(e)}
    
    def collect_ec2_instances(self):
        """Coleta informações de instâncias EC2"""
        logger.info("Coletando informações de instâncias EC2...")
        try:
            ec2_client = self.session.client('ec2')
            instances = ec2_client.describe_instances()
            
            instances_data = []
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_info = {
                        'instance_id': instance['InstanceId'],
                        'instance_type': instance['InstanceType'],
                        'state': instance['State']['Name'],
                        'launch_time': instance.get('LaunchTime', 'N/A'),
                        'private_ip': instance.get('PrivateIpAddress', 'N/A'),
                        'public_ip': instance.get('PublicIpAddress', 'N/A')
                    }
                    instances_data.append(instance_info)
            
            self.data['ec2_instances'] = {
                'total_instances': len(instances_data),
                'instances': instances_data
            }
        except Exception as e:
            self.data['ec2_instances'] = {'error': str(e)}
    
    def collect_rds(self):
        """Coleta informações de RDS"""
        logger.info("Coletando informações de RDS...")
        try:
            rds_client = self.session.client('rds')
            db_instances = rds_client.describe_db_instances()
            
            rds_data = []
            for db in db_instances['DBInstances']:
                db_info = {
                    'identifier': db['DBInstanceIdentifier'],
                    'engine': db['Engine'],
                    'status': db['DBInstanceStatus'],
                    'endpoint': db.get('Endpoint', {}).get('Address', 'N/A'),
                    'instance_class': db['DBInstanceClass']
                }
                rds_data.append(db_info)
            
            self.data['rds'] = {
                'total_instances': len(rds_data),
                'instances': rds_data
            }
        except Exception as e:
            self.data['rds'] = {'error': str(e)}
    
    def collect_api_gateway(self):
        """Coleta informações do API Gateway"""
        logger.info("Coletando informações do API Gateway...")
        try:
            apigw_client = self.session.client('apigateway')
            apis = apigw_client.get_rest_apis()
            
            apis_data = []
            for api in apis['items']:
                api_info = {
                    'id': api['id'],
                    'name': api['name'],
                    'created_date': api.get('createdDate', 'N/A')
                }
                apis_data.append(api_info)
            
            self.data['api_gateway'] = {
                'total_apis': len(apis_data),
                'apis': apis_data
            }
        except Exception as e:
            self.data['api_gateway'] = {'error': str(e)}
    
    def collect_cloudfront(self):
        """Coleta informações do CloudFront"""
        logger.info("Coletando informações do CloudFront...")
        try:
            cf_client = self.session.client('cloudfront')
            distributions = cf_client.list_distributions()
            
            dist_data = []
            if 'Items' in distributions['DistributionList']:
                for dist in distributions['DistributionList']['Items']:
                    dist_info = {
                        'id': dist['Id'],
                        'domain_name': dist['DomainName'],
                        'status': dist['Status'],
                        'enabled': dist['Enabled']
                    }
                    dist_data.append(dist_info)
            
            self.data['cloudfront'] = {
                'total_distributions': len(dist_data),
                'distributions': dist_data
            }
        except Exception as e:
            self.data['cloudfront'] = {'error': str(e)}
    
    def collect_lambda(self):
        """Coleta informações do Lambda"""
        logger.info("Coletando informações do Lambda...")
        try:
            lambda_client = self.session.client('lambda')
            functions = lambda_client.list_functions()
            
            func_data = []
            for func in functions['Functions']:
                func_info = {
                    'name': func['FunctionName'],
                    'runtime': func.get('Runtime', 'N/A'),
                    'handler': func.get('Handler', 'N/A'),
                    'last_modified': func.get('LastModified', 'N/A')
                }
                func_data.append(func_info)
            
            self.data['lambda'] = {
                'total_functions': len(func_data),
                'functions': func_data
            }
        except Exception as e:
            self.data['lambda'] = {'error': str(e)}
    
    def collect_sns(self):
        """Coleta informações do SNS"""
        logger.info("Coletando informações do SNS...")
        try:
            sns_client = self.session.client('sns')
            topics = sns_client.list_topics()
            
            topics_data = []
            for topic in topics['Topics']:
                topic_arn = topic['TopicArn']
                topic_name = topic_arn.split(':')[-1]
                topics_data.append({
                    'name': topic_name,
                    'arn': topic_arn
                })
            
            self.data['sns'] = {
                'total_topics': len(topics_data),
                'topics': topics_data
            }
        except Exception as e:
            self.data['sns'] = {'error': str(e)}
    
    def collect_backup(self):
        """Coleta informações do AWS Backup"""
        logger.info("Coletando informações do AWS Backup...")
        try:
            backup_client = self.session.client('backup')
            backup_plans = backup_client.list_backup_plans()
            
            plans_data = []
            for plan in backup_plans['BackupPlansList']:
                plan_info = {
                    'id': plan['BackupPlanId'],
                    'name': plan['BackupPlanName'],
                    'creation_date': plan.get('CreationDate', 'N/A')
                }
                plans_data.append(plan_info)
            
            self.data['backup'] = {
                'total_plans': len(plans_data),
                'plans': plans_data
            }
        except Exception as e:
            self.data['backup'] = {'error': str(e)}
    
    def collect_eventbridge(self):
        """Coleta informações do EventBridge"""
        logger.info("Coletando informações do EventBridge...")
        try:
            events_client = self.session.client('events')
            rules = events_client.list_rules()
            
            rules_data = []
            for rule in rules['Rules']:
                rule_info = {
                    'name': rule['Name'],
                    'state': rule.get('State', 'N/A'),
                    'event_pattern': rule.get('EventPattern', 'N/A')
                }
                rules_data.append(rule_info)
            
            self.data['eventbridge'] = {
                'total_rules': len(rules_data),
                'rules': rules_data
            }
        except Exception as e:
            self.data['eventbridge'] = {'error': str(e)}
    
    def collect_load_balancers(self):
        """Coleta informações dos Load Balancers"""
        logger.info("Coletando informações dos Load Balancers...")
        try:
            elbv2_client = self.session.client('elbv2')
            load_balancers = elbv2_client.describe_load_balancers()
            
            lb_data = []
            for lb in load_balancers['LoadBalancers']:
                lb_info = {
                    'name': lb['LoadBalancerName'],
                    'type': lb['Type'],
                    'scheme': lb['Scheme'],
                    'state': lb['State']['Code'],
                    'dns_name': lb['DNSName']
                }
                lb_data.append(lb_info)
            
            self.data['load_balancers'] = {
                'total_load_balancers': len(lb_data),
                'load_balancers': lb_data
            }
        except Exception as e:
            self.data['load_balancers'] = {'error': str(e)}
    
    def collect_ecs(self):
        """Coleta informações do ECS"""
        logger.info("Coletando informações do ECS...")
        try:
            ecs_client = self.session.client('ecs')
            clusters = ecs_client.list_clusters()
            
            clusters_data = []
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                
                # Obter serviços do cluster
                services = ecs_client.list_services(cluster=cluster_arn)
                
                cluster_info = {
                    'name': cluster_name,
                    'arn': cluster_arn,
                    'services_count': len(services['serviceArns'])
                }
                clusters_data.append(cluster_info)
            
            self.data['ecs'] = {
                'total_clusters': len(clusters_data),
                'clusters': clusters_data
            }
        except Exception as e:
            self.data['ecs'] = {'error': str(e)}
    
    def collect_iam_identity_center(self):
        """Coleta informações do IAM Identity Center (SSO)"""
        logger.info("Coletando informações do IAM Identity Center...")
        try:
            sso_client = self.session.client('sso-admin')
            instances = sso_client.list_instances()
            
            sso_data = []
            for instance in instances['Instances']:
                instance_info = {
                    'instance_arn': instance['InstanceArn'],
                    'identity_store_id': instance['IdentityStoreId']
                }
                sso_data.append(instance_info)
            
            self.data['iam_identity_center'] = {
                'total_instances': len(sso_data),
                'instances': sso_data,
                'status': 'Ativo' if sso_data else 'Inativo'
            }
        except Exception as e:
            self.data['iam_identity_center'] = {'status': 'Não disponível', 'error': str(e)}
    
    def collect_all_data(self):
        """Coleta todos os dados AWS"""
        logger.info("Iniciando coleta de dados AWS...")
        
        collection_methods = [
            self.collect_account_summary,
            self.collect_organizations,
            self.collect_control_tower,
            self.collect_vpc_summary,
            self.collect_route53,
            self.collect_ec2_instances,
            self.collect_rds,
            self.collect_api_gateway,
            self.collect_cloudfront,
            self.collect_lambda,
            self.collect_sns,
            self.collect_backup,
            self.collect_eventbridge,
            self.collect_load_balancers,
            self.collect_ecs,
            self.collect_iam_identity_center
        ]
        
        for method in collection_methods:
            try:
                method()
            except Exception as e:
                logger.warning(f"Erro ao executar {method.__name__}: {str(e)}")
        
        logger.info("Coleta de dados concluída.")
    
    def setup_document_styles(self):
        """Configura estilos do documento"""
        # Título principal
        title_style = self.doc.styles.add_style('CustomTitle', WD_STYLE_TYPE.PARAGRAPH)
        title_style.font.name = 'Arial'
        title_style.font.size = Pt(24)
        title_style.font.bold = True
        title_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_style.paragraph_format.space_after = Pt(12)
        
        # Cabeçalho de seção
        heading_style = self.doc.styles.add_style('CustomHeading', WD_STYLE_TYPE.PARAGRAPH)
        heading_style.font.name = 'Arial'
        heading_style.font.size = Pt(16)
        heading_style.font.bold = True
        heading_style.paragraph_format.space_before = Pt(12)
        heading_style.paragraph_format.space_after = Pt(6)
        
        # Parágrafo normal
        normal_style = self.doc.styles['Normal']
        normal_style.font.name = 'Arial'
        normal_style.font.size = Pt(11)
    
    def add_cover_page(self):
        """Adiciona capa do documento"""
        logger.info("Criando capa do documento...")
        
        # Logo (se existir)
        if os.path.exists('logo.png'):
            try:
                p = self.doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.add_picture('logo.png', width=Inches(2))
            except Exception as e:
                logger.warning(f"Erro ao inserir logo: {str(e)}")
        
        # Título
        title = self.doc.add_paragraph('AWS RUNBOOK', style='CustomTitle')
        
        # Subtítulo com nome da conta
        subtitle = self.doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle_run = subtitle.add_run(f"Conta: {self.account_name}")
        subtitle_run.font.size = Pt(14)
        subtitle_run.font.bold = True
        
        # Data de geração
        date_p = self.doc.add_paragraph()
        date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_run = date_p.add_run(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        date_run.font.size = Pt(12)
        
        # Quebra de página
        self.doc.add_page_break()
    
    def add_table_of_contents(self):
        """Adiciona sumário"""
        logger.info("Criando sumário...")
        
        toc_title = self.doc.add_paragraph('SUMÁRIO', style='CustomTitle')
        
        sections = [
            "1. Resumo da Conta",
            "2. AWS Organizations",
            "3. AWS Control Tower",
            "4. Resumo de VPCs",
            "5. Route 53 (DNS)",
            "6. Instâncias EC2",
            "7. RDS (Banco de Dados)",
            "8. API Gateway",
            "9. CloudFront",
            "10. Lambda Functions",
            "11. SNS (Notificações)",
            "12. AWS Backup",
            "13. EventBridge",
            "14. Load Balancers",
            "15. ECS (Containers)",
            "16. IAM Identity Center"
        ]
        
        for section in sections:
            p = self.doc.add_paragraph(section)
            p.paragraph_format.left_indent = Inches(0.5)
        
        self.doc.add_page_break()
    
    def add_section(self, title, description, data_key):
        """Adiciona uma seção ao documento"""
        # Título da seção
        self.doc.add_paragraph(title, style='CustomHeading')
        
        # Descrição
        self.doc.add_paragraph(description)
        
        # Dados
        if data_key in self.data:
            data = self.data[data_key]
            
            if 'error' in data:
                error_p = self.doc.add_paragraph(f"Erro: {data['error']}")
                error_p.runs[0].font.color.rgb = None  # Vermelho seria ideal
            else:
                self.create_data_table(data)
        else:
            self.doc.add_paragraph("Dados não disponíveis")
        
        self.doc.add_paragraph()  # Espaçamento
    
    def create_data_table(self, data):
        """Cria uma tabela com os dados"""
        if isinstance(data, dict):
            # Criar tabela simples para dados de dicionário
            if any(isinstance(v, list) for v in data.values()):
                # Se há listas, criar tabelas específicas
                for key, value in data.items():
                    if isinstance(value, list) and value:
                        if key in ['instances', 'zones', 'apis', 'distributions', 'functions', 
                                 'topics', 'plans', 'rules', 'load_balancers', 'clusters']:
                            self.create_detailed_table(key, value)
                    elif not isinstance(value, list):
                        p = self.doc.add_paragraph(f"{key.replace('_', ' ').title()}: {value}")
            else:
                # Tabela simples para dados básicos
                table = self.doc.add_table(rows=1, cols=2)
                table.style = 'Table Grid'
                
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = 'Propriedade'
                hdr_cells[1].text = 'Valor'
                
                for key, value in data.items():
                    if not isinstance(value, (list, dict)):
                        row_cells = table.add_row().cells
                        row_cells[0].text = key.replace('_', ' ').title()
                        row_cells[1].text = str(value)
    
    def create_detailed_table(self, data_type, items):
        """Cria tabela detalhada para listas de itens"""
        if not items:
            return
        
        # Determinar colunas baseado no tipo de dados
        if data_type == 'instances' and 'instance_id' in items[0]:
            # EC2 Instances
            table = self.doc.add_table(rows=1, cols=5)
            headers = ['Instance ID', 'Type', 'State', 'Private IP', 'Public IP']
            keys = ['instance_id', 'instance_type', 'state', 'private_ip', 'public_ip']
        elif data_type == 'instances' and 'identifier' in items[0]:
            # RDS Instances
            table = self.doc.add_table(rows=1, cols=5)
            headers = ['Identifier', 'Engine', 'Status', 'Endpoint', 'Class']
            keys = ['identifier', 'engine', 'status', 'endpoint', 'instance_class']
        elif data_type == 'zones':
            # Route 53 Zones
            table = self.doc.add_table(rows=1, cols=3)
            headers = ['Name', 'ID', 'Record Count']
            keys = ['name', 'id', 'record_count']
        elif data_type == 'functions':
            # Lambda Functions
            table = self.doc.add_table(rows=1, cols=4)
            headers = ['Name', 'Runtime', 'Handler', 'Last Modified']
            keys = ['name', 'runtime', 'handler', 'last_modified']
        else:
            # Tabela genérica
            if items and isinstance(items[0], dict):
                first_item = items[0]
                headers = list(first_item.keys())
                keys = headers
                table = self.doc.add_table(rows=1, cols=len(headers))
            else:
                return
        
        table.style = 'Table Grid'
        
        # Cabeçalhos
        hdr_cells = table.rows[0].cells
        for i, header in enumerate(headers):
            hdr_cells[i].text = header.replace('_', ' ').title()
        
        # Dados
        for item in items[:10]:  # Limitar a 10 itens para não sobrecarregar
            row_cells = table.add_row().cells
            for i, key in enumerate(keys):
                if i < len(row_cells):
                    value = item.get(key, 'N/A')
                    if isinstance(value, datetime):
                        value = value.strftime('%d/%m/%Y %H:%M')
                    row_cells[i].text = str(value)
        
        if len(items) > 10:
            self.doc.add_paragraph(f"... e mais {len(items) - 10} itens")
    
    def generate_document(self):
        """Gera o documento completo"""
        logger.info("Gerando documento Word...")
        
        # Configurar estilos
        self.setup_document_styles()
        
        # Capa
        self.add_cover_page()
        
        # Sumário
        self.add_table_of_contents()
        
        # Seções
        sections = [
            ("1. RESUMO DA CONTA", "Informações gerais da conta AWS", "account_summary"),
            ("2. AWS ORGANIZATIONS", "Status e configuração do AWS Organizations", "organizations"),
            ("3. AWS CONTROL TOWER", "Status do AWS Control Tower", "control_tower"),
            ("4. RESUMO DE VPCs", "Redes virtuais privadas e configurações", "vpc_summary"),
            ("5. ROUTE 53 (DNS)", "Domínios e zonas DNS configuradas", "route53"),
            ("6. INSTÂNCIAS EC2", "Servidores virtuais em execução", "ec2_instances"),
            ("7. RDS (BANCO DE DADOS)", "Instâncias de banco de dados", "rds"),
            ("8. API GATEWAY", "APIs registradas e configuradas", "api_gateway"),
            ("9. CLOUDFRONT", "Distribuições CDN ativas", "cloudfront"),
            ("10. LAMBDA FUNCTIONS", "Funções serverless configuradas", "lambda"),
            ("11. SNS (NOTIFICAÇÕES)", "Tópicos de notificação", "sns"),
            ("12. AWS BACKUP", "Planos e políticas de backup", "backup"),
            ("13. EVENTBRIDGE", "Regras de eventos configuradas", "eventbridge"),
            ("14. LOAD BALANCERS", "Balanceadores de carga", "load_balancers"),
            ("15. ECS (CONTAINERS)", "Clusters e serviços de containers", "ecs"),
            ("16. IAM IDENTITY CENTER", "Centro de identidade e SSO", "iam_identity_center")
        ]
        
        for title, description, data_key in sections:
            self.add_section(title, description, data_key)
        
        # Salvar documento
        filename = f"runbook_{self.account_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        self.doc.save(filename)
        logger.info(f"Documento salvo como: {filename}")
        return filename
    
    def run(self):
        """Executa o gerador completo"""
        logger.info("=== AWS RUNBOOK GENERATOR ===")
        
        # Configurar AWS
        if not self.setup_aws_session():
            return False
        
        # Coletar dados
        self.collect_all_data()
        
        # Gerar documento
        filename = self.generate_document()
        
        logger.info(f"Runbook gerado com sucesso: {filename}")
        return True

def main():
    """Função principal"""
    generator = AWSRunbookGenerator()
    
    try:
        success = generator.run()
        if success:
            print("\n✅ Runbook gerado com sucesso!")
        else:
            print("\n❌ Falha na geração do runbook.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        print(f"\n❌ Erro inesperado: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
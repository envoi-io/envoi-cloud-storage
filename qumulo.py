import argparse
import boto3


class EnvoiStorageQumuloAwsCreateClusterCommand(EnvoiCommand):

    @classmethod
    def init_parser(cls, parent_parsers=None, **kwargs):
        parser = super().init_parser(parent_parsers=parent_parsers, **kwargs)
        parser.add_argument('--template-url', type=str,
                            default="https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/cnq-advanced.template.yaml",
                            help='The URL to the CloudFormation template')
        parser.add_argument('--stack-name', type=str, default="Qumulo",
                            help='Stack name.')
        parser.add_argument('--aws-region', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS region. (defaults to the value from the AWS_DEFAULT_REGION environment variable)')
        parser.add_argument('--aws-profile', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS profile. (defaults to the value from the AWS_PROFILE environment variable)')
        parser.add_argument('--cfn-role-arn', type=str, required=False,
                            help='IAM Role to use when creating the CloudFormation stack')

        # AWS Template Configuration - Cloud Native Qumulo - Advanced v6.3
        parser.add_argument("--qs-s3-bucket-name", type=str, required=True,
                            help="Qumulo software S3 bucket name")
        parser.add_argument("--qs-s3-key-prefix", type=str, required=True,
                            help="Qumulo software S3 key prefix")
        parser.add_argument("--qs-s3-region", type=str, required=True,
                            help="Qumulo software S3 region")
        parser.add_argument("--key-pair-name", required=True,
                            help="Name of an existing EC2 KeyPair to enable SSH access to the node")
        parser.add_argument("--env-type", type=str, required=True,
                            choices=["dev", "prod"],
                            help="Environment type (dev or prod)")

        # AWS network configuration
        parser.add_argument("--vpc-id", required=True,
                            help="Qumulo cluster VPC ID")
        parser.add_argument("--security-group-cidr-1", default="10.0.0.0/16",
                            help="Security group CIDR 1")
        parser.add_argument("--security-group-cidr-2", default="", help="Security group CIDR 2")
        parser.add_argument("--security-group-cidr-3", default="", help="Security group CIDR 3")
        parser.add_argument("--security-group-cidr-4", default="", help="Security group CIDR 4")
        parser.add_argument("--number-azs", type=str, default="1", choices=["1", "3", "4"], help="Number of Availability Zones (1, 3, or 4)")
        parser.add_argument("--private-subnet-ids", type=str, required=True,
                            help="Comma-separated list of private subnet IDs")
        parser.add_argument("--second-private-subnet-id", type=str, default="", help="Second private subnet ID for R53 Resolver")
        parser.add_argument("--q-nlb", default="NO", choices=["YES", "NO"], help="Deploy an AWS network load balancer")
        parser.add_argument("--q-nlb-private-subnet-ids", type=str, default="", help="Comma-separated list of private subnet IDs for the NLB")
        parser.add_argument("--qfqdn", type=str, default="", help="FQDN for Qumulo DNS Resolver")

        # Qumulo file data platform configuration
        parser.add_argument("--q-ami-id", type=str, default="Ubuntu-Lookup", help="Qumulo AMI ID")
        parser.add_argument("--q-debian-package", default="DEB", choices=["DEB", "RPM"], help="Debian or RPM package")
        parser.add_argument("--q-persistent-storage-type", type=str, default="hot_s3_int", choices=["hot_s3_std", "hot_s3_int", "cold_s3_ia", "cold_s3_gir"], help="Hot or Cold Cluster storage type")
        parser.add_argument("--q-persistent-storage-deployment-stack-name", type=str, default="", help="Stack name from the persistent storage CloudFormation deployment")
        parser.add_argument("--q-persistent-storage-bucket-policy", type=str, default="YES", choices=["YES", "NO"], help="Policy for persistent storage S3 Buckets")
        parser.add_argument("--q-instance-type", default="i4i.4xlarge", help="Qumulo EC2 instance type")
        parser.add_argument("--q-node-count", default="3", help="Number of Qumulo EC2 instances")
        parser.add_argument("--q-min-floating-ip-per-node", type=str, default="1", choices=["1", "2", "3", "4"], help="Minimum Floating IPs per node")
        parser.add_argument("--q-target-node-count", type=str, default="NO REDUCTION", help="Target Number of Qumulo EC2 instances")
        parser.add_argument("--q-replacement-cluster", type=str, default="NO", choices=["YES", "NO"], help="Replacement Cluster")
        parser.add_argument("--q-existing-deployment-stack-name", type=str, default="", help="Existing Deployment CloudFormation Stack Name")
        parser.add_argument("--q-write-cache-type", default="gp3", choices=["gp2", "gp3", "io2"], help="Write cache type")
        parser.add_argument("--q-write-cache-tput", default="Use Qumulo Default", choices=["Use Qumulo Default", "125", "250", "500", "750", "1000"], help="Write cache throughput")
        parser.add_argument("--q-write-cache-iops", default="Use Qumulo Default", choices=["Use Qumulo Default", "1000", "2000", "3000", "4000", "5000", "6000", "7000", "8000", "9000", "10000", "11000", "12000", "13000", "14000", "15000", "16000"], help="Write cache IOPS")
        parser.add_argument("--q-boot-dkv-type", default="gp3", choices=["gp2", "gp3"], help="Boot/DKV type")
        parser.add_argument("--q-cluster-version", default="7.5.0", help="Qumulo software version")
        parser.add_argument("--q-cluster-name", required=True, help="Qumulo cluster name")
        parser.add_argument("--q-cluster-admin-pwd", required=True, help="Qumulo cluster administrator password")
        parser.add_argument("--volumes-encryption-key", type=str, default="", help="EBS volumes encryption key")
        parser.add_argument("--q-permissions-boundary", default="", help="Qumulo permissions boundary policy name")
        parser.add_argument("--q-audit-log", default="NO", choices=["YES", "NO"], help="Qumulo audit-log messages to CloudWatch Logs")
        parser.add_argument("--term-protection", default="YES", choices=["YES", "NO"], help="Termination protection")
        return parser

    def run(self, opts=None):
        if opts is None:
            opts = self.opts
        cfn_client_args = {}
        add_from_namespace_to_dict_if_not_none(opts, 'aws_profile', cfn_client_args, 'profile_name')
        add_from_namespace_to_dict_if_not_none(opts, 'aws_region', cfn_client_args, 'region_name')

        client = boto3.client('cloudformation', **cfn_client_args)
        template_parameters = []

        # Map CLI args to CloudFormation parameters for cnq-advanced.template.yaml
        template_parameters_to_check = {
            'qs_s3_bucket_name': 'QSS3BucketName',
            'qs_s3_key_prefix': 'QSS3KeyPrefix',
            'qs_s3_region': 'QSS3BucketRegion',
            'key_pair_name': 'KeyPair',
            'env_type': 'EnvType',
            'vpc_id': 'VPCId',
            'security_group_cidr_1': 'QSgCidr1',
            'security_group_cidr_2': 'QSgCidr2',
            'security_group_cidr_3': 'QSgCidr3',
            'security_group_cidr_4': 'QSgCidr4',
            'number_azs': 'NumberAZs',
            'private_subnet_ids': 'PrivateSubnetIDs',
            'second_private_subnet_id': 'SecondPrivateSubnetID',
            'q_nlb': 'QNlb',
            'q_nlb_private_subnet_ids': 'QNlbPrivateSubnetIDs',
            'qfqdn': 'QFQDN',
            'q_ami_id': 'QAmiID',
            'q_debian_package': 'QDebianPackage',
            'q_persistent_storage_type': 'QPersistentStorageType',
            'q_persistent_storage_deployment_stack_name': 'QPersistentStorageDeploymentStackName',
            'q_persistent_storage_bucket_policy': 'QPersistentStorageBucketPolicy',
            'q_instance_type': 'QInstanceType',
            'q_node_count': 'QNodeCount',
            'q_min_floating_ip_per_node': 'QMinFloatingIPperNode',
            'q_target_node_count': 'QTargetNodeCount',
            'q_replacement_cluster': 'QReplacementCluster',
            'q_existing_deployment_stack_name': 'QExistingDeploymentStackName',
            'q_write_cache_type': 'QWriteCacheType',
            'q_write_cache_tput': 'QWriteCacheTput',
            'q_write_cache_iops': 'QWriteCacheIops',
            'q_boot_dkv_type': 'QBootDKVType',
            'q_cluster_version': 'QClusterVersion',
            'q_cluster_name': 'QClusterName',
            'q_cluster_admin_pwd': 'QClusterAdminPwd',
            'volumes_encryption_key': 'VolumesEncryptionKey',
            'q_permissions_boundary': 'QPermissionsBoundary',
            'q_audit_log': 'QAuditLog',
            'term_protection': 'TermProtection',
        }

        for opts_param_name, template_param_name in template_parameters_to_check.items():
            if hasattr(opts, opts_param_name):
                value = getattr(opts, opts_param_name)
                if value is not None:
                    # Handle list parameters (comma-separated string to list)
                    if template_param_name in ['PrivateSubnetIDs', 'QNlbPrivateSubnetIDs']:
                        if isinstance(value, str):
                            value = [v.strip() for v in value.split(',') if v.strip()]
                    template_parameters.append({'ParameterKey': template_param_name, 'ParameterValue': value})

        cfn_create_stack_args = {
            'StackName': opts.stack_name,
            'Parameters': template_parameters,
            'Capabilities': ['CAPABILITY_IAM']
        }

        if hasattr(opts, 'template_url'):
            cfn_create_stack_args['TemplateURL'] = opts.template_url
        else:
            raise ValueError("Missing required parameter template_url")

        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        response = client.create_stack(**cfn_create_stack_args)
        stack_id = response['StackId']
        if stack_id is not None:
            response = f"Stack ID {stack_id}"

        return response


class EnvoiStorageQumuloLegacyAwsCreateClusterCommand(EnvoiCommand):

    @classmethod
    def init_parser(cls, parent_parsers=None, **kwargs):
        parser = super().init_parser(parent_parsers=parent_parsers, **kwargs)
        parser.add_argument('--template-url', type=str,
                            default="https://envoi-prod-files-public.s3.amazonaws.com"
                                    "/qumulo/cloud-formation/templates/qumulo.cfn-template.json",
                            help='The URL to the CloudFormation template')
        parser.add_argument('--stack-name', type=str, default="Qumulo",
                            help='Stack name.')
        parser.add_argument('--aws-region', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS region. (defaults to the value from the AWS_DEFAULT_REGION environment variable)')
        parser.add_argument('--aws-profile', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS profile. (defaults to the value from the AWS_PROFILE environment variable)')
        parser.add_argument('--cfn-role-arn', type=str, required=False,
                            help='IAM Role to use when creating the CloudFormation stack')
        parser.add_argument("--cluster-name", type=str, required=True,
                            help="Qumulo cluster name (2-15 alpha-numeric characters and -)")
        parser.add_argument("--key-pair-name", required=True,
                            help="Name of an existing EC2 KeyPair to enable SSH access to the node")
        parser.add_argument("--vpc-id", required=True,
                            help="Qumulo cluster VPC ID")
        parser.add_argument("--subnet-id", type=str, required=True, help="Subnet ID")

        # Optional arguments
        parser.add_argument("--iam-instance-profile-name", default="",
                            help="The name (*not* the ARN) of the IAM instance profile to be "
                                 "assigned to each instance in the cluster.")
        parser.add_argument("--instance-type", default="c5n.xlarge",
                            help="EC2 instance type for Qumulo node")
        parser.add_argument("--security-group-cidr", default="0.0.0.0/0",
                            help="Security group CIDR")
        parser.add_argument("--volumes-encryption-key", type=str, default="",
                            help="Encryption Key for the Volumes")

        return parser

    def run(self, opts=None):
        if opts is None:
            opts = self.opts
        cfn_client_args = {}
        add_from_namespace_to_dict_if_not_none(opts, 'aws_profile', cfn_client_args, 'profile_name')
        add_from_namespace_to_dict_if_not_none(opts, 'aws_region', cfn_client_args, 'region_name')

        client = boto3.client('cloudformation', **cfn_client_args)
        template_parameters = []

        template_parameters_to_check = {
            'cluster_name': 'ClusterName',
            'iam_instance_profile': 'IamInstanceProfile',
            'instance_type': 'InstanceType',
            'key_pair_name': 'KeyName',
            'vpc_id': 'VpcId',
            'subnet_id': 'SubnetId',
            'security_group_cidr': 'SgCidr',
            'volumes_encryption_key': 'VolumesEncryptionKey',
        }

        for opts_param_name, template_param_name in template_parameters_to_check.items():
            if hasattr(opts, opts_param_name):
                value = getattr(opts, opts_param_name)
                if value is not None:
                    template_parameters.append({'ParameterKey': template_param_name, 'ParameterValue': value})

        cfn_create_stack_args = {
            'StackName': opts.stack_name,
            'Parameters': template_parameters,
            'Capabilities': ['CAPABILITY_IAM']
        }

        if hasattr(opts, 'template_url'):
            cfn_create_stack_args['TemplateURL'] = opts.template_url
        else:
            raise ValueError("Missing required parameter template_url")

        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        response = client.create_stack(**cfn_create_stack_args)
        stack_id = response['StackId']
        if stack_id is not None:
            response = f"Stack ID {stack_id}"

        return response


class EnvoiStorageQumuloAwsCommand(EnvoiCommand):
    subcommands = {
        'create-cluster': EnvoiStorageQumuloAwsCreateClusterCommand,
    }


class EnvoiStorageQumuloCommand(EnvoiCommand):
    subcommands = {
        'aws': EnvoiStorageQumuloAwsCommand,
    }


# AWSTemplateFormatVersion: "2010-09-09"
#
# # MIT License
# #
# # Copyright (c) 2025 Qumulo, Inc.
# #
# # Permission is hereby granted, free of charge, to any person obtaining a copy
# # of this software and associated documentation files (the "Software"), to deal
# # in the Software without restriction, including without limitation the rights
# # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# # copies of the Software, and to permit persons to whom the Software is
# # furnished to do so, subject to the following conditions:
# #
# # The above copyright notice and this permission notice shall be included in all
# # copies or substantial portions of the Software.
# #
# # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# # SOFTWARE.
#
# Description: This is the main template to spin up a Cloud Native Qumulo Cluster with all options available in an existing VPC.  It calls cnq.cft.yaml to instantiate the infrastructure. (qs-1s6n2i6af)
#
# Metadata:
#   AWS::CloudFormation::Interface:
#     ParameterGroups:
#       - Label:
#           default: AWS Template Configuration - Cloud Native Qumulo - Advanced v6.3
#         Parameters:
#           - QSS3BucketName
#           - QSS3KeyPrefix
#           - QSS3BucketRegion
#           - KeyPair
#           - EnvType
#
#       - Label:
#           default: AWS network configuration
#         Parameters:
#           - VPCId
#           - QSgCidr1
#           - QSgCidr2
#           - QSgCidr3
#           - QSgCidr4
#           - NumberAZs
#           - PrivateSubnetIDs
#           - QNlb
#           - QNlbPrivateSubnetIDs
#           - QFQDN
#           - SecondPrivateSubnetID
#
#       - Label:
#           default: Qumulo file data platform configuration
#         Parameters:
#           - QAmiID
#           - QDebianPackage
#           - QPersistentStorageDeploymentStackName
#           - QPersistentStorageType
#           - QPersistentStorageBucketPolicy
#           - QInstanceType
#           - QNodeCount
#           - QMinFloatingIPperNode
#           - QTargetNodeCount
#           - QReplacementCluster
#           - QExistingDeploymentStackName
#           - QWriteCacheType
#           - QWriteCacheTput
#           - QWriteCacheIops
#           - QBootDKVType
#           - QClusterVersion
#           - QClusterName
#           - QClusterAdminPwd
#           - VolumesEncryptionKey
#           - QPermissionsBoundary
#           - QAuditLog
#           - TermProtection
#
#     ParameterLabels:
#       QSS3BucketName:
#         default: "S3 bucket name"
#       QSS3KeyPrefix:
#         default: "S3 key prefix"
#       QSS3BucketRegion:
#         default: "S3 bucket Region"
#       QFQDN:
#         default: "FQDN for Qumulo DNS Resolver"
#       EnvType:
#         default: "Environment type"
#       KeyPair:
#         default: "EC2 key pair"
#       NumberAZs:
#         default: "Number of Availability Zones"
#       PrivateSubnetIDs:
#         default: "Private subnet ID(s)"
#       SecondPrivateSubnetID:
#         default: "Second private subnet ID for R53 Resolver"
#       QAmiID:
#         default: "Qumulo AMI ID"
#       QAuditLog:
#         default: "Qumulo audit-log messages to CloudWatch Logs"
#       QBootDKVType:
#         default: "Boot/DKV type"
#       QClusterAdminPwd:
#         default: "Qumulo cluster administrator password"
#       QClusterName:
#         default: "Qumulo cluster name"
#       QClusterVersion:
#         default: "Qumulo software version"
#       QDebianPackage:
#         default: "Debian or RPM package"
#       QPersistentStorageType:
#         default: "Hot or Cold Cluster"
#       QExistingDeploymentStackName:
#         default: "Existing Deployment CloudFormation Stack Name"
#       QInstanceType:
#         default: "Qumulo EC2 instance type"
#       QNlb:
#         default: "Deploy an AWS network load balancer"
#       QNlbPrivateSubnetIDs:
#         default: "AWS private subnet ID(s) for the network load balancer"
#       QNodeCount:
#         default: "Number of Qumulo EC2 instances"
#       QMinFloatingIPperNode:
#         default: "The minimum Floating IPs per node"
#       QTargetNodeCount:
#         default: "Target Number of Qumulo EC2 instances"
#       QPermissionsBoundary:
#         default: "Qumulo permissions boundary policy name"
#       QPersistentStorageDeploymentStackName:
#         default: "Stack name from the persistent storage CloudFormation deployment"
#       QPersistentStorageBucketPolicy:
#         default: "Policy for persistent storage S3 Buckets"
#       QReplacementCluster:
#         default: "Replacement Cluster"
#       QSgCidr1:
#         default: "CIDR #1 for the Qumulo security group"
#       QSgCidr2:
#         default: "CIDR #2 for the Qumulo security group"
#       QSgCidr3:
#         default: "CIDR #3 for the Qumulo security group"
#       QSgCidr4:
#         default: "CIDR #4 for the Qumulo security group"
#       QWriteCacheIops:
#         default: "Write cache IOPS"
#       QWriteCacheTput:
#         default: "Write cache throughput"
#       QWriteCacheType:
#         default: "Write cache type"
#       TermProtection:
#         default: "Termination protection "
#       VPCId:
#         default: "VPC ID"
#       VolumesEncryptionKey:
#         default: "EBS volumes encryption key"
#
# Parameters:
#
#   QSS3BucketName:
#     AllowedPattern: '^[0-9a-zA-Z]+([0-9a-zA-Z-]*[0-9a-zA-Z])*$'
#     ConstraintDescription:
#       The bucket name can include numbers, lowercase
#       letters, uppercase letters, and hyphens (-). It cannot start or end with a
#       hyphen (-).
#     Default: my-bucket
#     Description:
#       'Name of the S3 bucket that contains your CloudFormation assets.'
#     Type: String
#
#   QSS3BucketRegion:
#     Default: us-west-2
#     Description: 'AWS Region of the S3 bucket that contains your CloudFormation assets.'
#     Type: String
#
#   QSS3KeyPrefix:
#     AllowedPattern: '^[0-9a-zA-Z-/.]*$'
#     ConstraintDescription:
#       The S3 key prefix can include numbers, lowercase letters,
#       uppercase letters, hyphens (-), and forward slashes (/).
#     Default: aws-cloudformation-cnq/
#     Description:
#       'S3 prefix (ie path) to your CloudFormation assets.'
#     Type: String
#
#   QFQDN:
#     AllowedPattern: '^$|^([a-zA-Z0-9-]+\..+)$'
#     Default: ""
#     Description: "(Optional) To create a Route 53 resolver enter a fully qualified domain name (FQDN).
#       The R53 Resolver will forward DNS Queries to the Qumulo Cluster for Floating IP resolution
#       You may use the .local suffix, e.g., qumulo.companyname.local. If your VPC already has a
#       means of DNS resolution for Qumulo Floating IPs, keep this value blank."
#     MaxLength: '255'
#     Type: String
#
#   EnvType:
#     AllowedValues:
#       - dev
#       - prod
#     Default: prod
#     Description: 'Choose "prod" if you are not deploying into a development
#       environment.'
#     Type: String
#
#   KeyPair:
#     Default: mykeypair
#     Description: Name of the key pair to be used to connect to your EC2 instances.
#     Type: AWS::EC2::KeyPair::KeyName
#
#   NumberAZs:
#     AllowedValues:
#       - "1"
#       - "3"
#       - "4"
#     Default: "1"
#     Description: Single-AZ=1, Multi-AZ=3 or 4
#     Type: String
#
#   PrivateSubnetIDs:
#     Description: ID of the private subnet for a single AZ deployment.  Select
#      multiple subnets matching your number of AZs selected above for multi-AZ
#      deployment.
#     Type: List<AWS::EC2::Subnet::Id>
#
#   SecondPrivateSubnetID:
#     Description: At least one subnet ID must be selected. A second private subnet ID, in a unique AZ other than the cluster AZ, for single AZ clusters.
#       This is then used to build a R53 Resolver to forward DNS Queries to the Qumulo Cluster for Floating IP resolution.
#       This subnet is only used if an Qumulo FQDN name was provided.
#     Type: AWS::EC2::Subnet::Id
#
#   QAmiID:
#     Default: Ubuntu-Lookup
#     Description: "Amazon Machine Image (AMI) ID for an Ubuntu (deb) or RHL (rpm).  Leave it as Ubuntu Lookup if you don't
#       have an AMI to specify."
#     Type: String
#
#   QAuditLog:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Default: "NO"
#     Description: Choose YES to create a CloudWatch Logs group for the Qumulo cluster
#       that captures all Qumulo audit-log activity.
#     Type: String
#
#   QBootDKVType:
#     AllowedValues:
#       - gp2
#       - gp3
#     Default: gp3
#     Description: "Choose the EBS Boot Drive and DKV type: gp2 or gp3.  Default is gp3."
#     Type: String
#
#   QClusterAdminPwd:
#     AllowedPattern: "^(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&\\-_])[A-Za-z\\d@$!%*?&\\-_]{8,}$"
#     Description: "Minimum 8 characters. Must include one each of the following:
#       uppercase letter, lowercase letter, and special character."
#     MaxLength: 128
#     MinLength: 8
#     NoEcho: "true"
#     Type: String
#
#   QClusterName:
#     AllowedPattern: "^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$"
#     Default: CNQ
#     Description: Alphanumeric string between 2 and 15 characters. Dash (-) is
#       allowed if not the first or last character.
#     MaxLength: 15
#     MinLength: 2
#     Type: String
#
#   QClusterVersion:
#     Default: "7.5.0"
#     Description: "This selects the folder within the 'qumulo-core-install' directory
#       like:
#       'QSS3BucketName'/'QSS3BucketPrefix'/qumulo-core-install/'QClusterVersion'.
#       Only applicable for package installs."
#     MaxLength: 11
#     MinLength: 5
#     Type: String
#
#   QDebianPackage:
#     AllowedValues:
#       - "DEB"
#       - "RPM"
#     Default: "DEB"
#     Description: "Debian or RPM Qumulo Core package to install."
#     Type: String
#
#   QPersistentStorageType:
#     AllowedValues:
#       - hot_s3_std
#       - hot_s3_int
#       - cold_s3_ia
#       - cold_s3_gir
#     Default: hot_s3_int
#     Description: "Choose a Hot or Cold storage type and S3 storage class: std=Standard, int=Intelligent-Tiering, ia=Infrequent-Access, gir=Glacier Instant Retrieval"
#     Type: String
#
#   QExistingDeploymentStackName:
#     Default: ""
#     Description: IF ReplacementCluster=YES an existing deployment CloudFormation
#       Stack Name must be specified
#     Type: String
#
#   QInstanceType:
#     AllowedValues:
#       - i4i.xlarge
#       - i4i.2xlarge
#       - i4i.4xlarge
#       - i4i.8xlarge
#       - i4i.12xlarge
#       - i4i.16xlarge
#       - i4i.24xlarge
#       - i4i.32xlarge
#       - i7i.2xlarge
#       - i7i.4xlarge
#       - i7i.8xlarge
#       - i7i.12xlarge
#       - i7i.16xlarge
#       - i7i.24xlarge
#       - i7ie.xlarge
#       - i7ie.2xlarge
#       - i7ie.3xlarge
#       - i7ie.6xlarge
#       - i7ie.12xlarge
#       - i7ie.18xlarge
#       - i7ie.24xlarge
#       - i3en.xlarge
#       - i3en.2xlarge
#       - i3en.3xlarge
#       - i3en.6xlarge
#       - i3en.12xlarge
#       - i3en.24xlarge
#       - m6idn.xlarge
#       - m6idn.2xlarge
#       - m6idn.4xlarge
#       - m6idn.8xlarge
#       - m6idn.12xlarge
#       - m6idn.16xlarge
#       - m6idn.24xlarge
#       - m6idn.32xlarge
#       - m6i.xlarge
#       - m6i.2xlarge
#       - m6i.4xlarge
#       - m6i.8xlarge
#       - m6i.12xlarge
#       - m6i.16xlarge
#     Default: i4i.4xlarge
#     Description: EC2 instance type for Qumulo nodes.
#     Type: String
#
#   QNlb:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Default: "NO"
#     Description: Choose YES to deploy a single AZ NLB.  Multi-AZ deployments always
#      deploy with an NLB.  Only choose YES to override the private subnets above
#      for a multi-AZ deployemnt with alternate subnets in the same AZs. This will
#      negate any Route53 PHZ options below and disable floating IPs on the
#      cluster.
#     Type: String
#
#   QNlbPrivateSubnetIDs:
#     Description: At least one subnet ID must be selected. These subnet ID(s) are
#       only used if YES was selected for QNlb above.
#     Type: List<AWS::EC2::Subnet::Id>
#
#   QNodeCount:
#     AllowedValues:
#       - "1"
#       - "3"
#       - "4"
#       - "5"
#       - "6"
#       - "7"
#       - "8"
#       - "9"
#       - "10"
#       - "11"
#       - "12"
#       - "13"
#       - "14"
#       - "15"
#       - "16"
#       - "17"
#       - "18"
#       - "19"
#       - "20"
#       - "21"
#       - "22"
#       - "23"
#       - "24"
#     Default: "3"
#     Description: "Total number of EC2 instances, or nodes, in the Qumulo cluster
#       (3-24 or 1). You can use this field to add nodes with a CloudFormation stack
#       update after initial provisioning.  You can use this field to remove unused
#       resources AFTER doing a stack update with 'Target Number of Qumulo EC2 Instances'"
#     Type: String
#
#   QMinFloatingIPperNode:
#     Description: "1 to 4 (1 Default)"
#     AllowedValues:
#       - "1"
#       - "2"
#       - "3"
#       - "4"
#     Type: String
#     Default: "1"
#
#   QTargetNodeCount:
#     AllowedValues:
#       - "NO REDUCTION"
#       - "1"
#       - "3"
#       - "4"
#       - "5"
#       - "6"
#       - "7"
#       - "8"
#       - "9"
#       - "10"
#       - "11"
#       - "12"
#       - "13"
#       - "14"
#       - "15"
#       - "16"
#       - "17"
#       - "18"
#       - "19"
#       - "20"
#       - "21"
#       - "22"
#       - "23"
#     Default: "NO REDUCTION"
#     Description: "Total number of EC2 instances, or nodes DESIRED, in the Qumulo cluster
#       (3-23 or 1). You can use this field to REMOVE nodes with a CloudFormation stack
#       update after initial provisioning. After removing the nodes, set it back to NO REDUCTION,
#       and then adjust 'Number of Qumulo EC2 Instances' to the new size of the cluster, stack update, to delete leftover resources."
#     Type: String
#
#   QPermissionsBoundary:
#     Default: ""
#     Description: "(Optional) Apply an IAM permissions boundary policy to the Qumulo
#       IAM roles that are created for the Qumulo cluster and provisioning instance.
#       This is an account-based policy. Qumulo's IAM roles conform to the
#       least-privilege model."
#     Type: String
#
#   QPersistentStorageDeploymentStackName:
#     Description: "The CloudFormation stack name used for the persistent storage deployment"
#     Type: String
#
#   QPersistentStorageBucketPolicy:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Default: "YES"
#     Description: Choose YES to apply an S3 bucket policy with least privileges.  If disabled the buckets will be accessible to any user or machine in the AWS account.
#     Type: String
#
#   QReplacementCluster:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Default: "NO"
#     Description: Choose YES to build a new cluster that will replace an existing deployment.
#     Type: String
#
#   QSgCidr1:
#     AllowedPattern: "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9\
#       ]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9]))$"
#     Default: "10.0.0.0/16"
#     Description: An IPv4 CIDR block for specifying the generated security group's
#       allowed addresses for inbound traffic. Typically set to the VPC CIDR.
#     Type: String
#
#   QSgCidr2:
#     AllowedPattern: "^$|^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([\
#       0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9])\
#       )$"
#     Default: ""
#     Description: (Optional) An IPv4 CIDR block for specifying the generated security
#       group's allowed addresses for inbound traffic.
#     Type: String
#
#   QSgCidr3:
#     AllowedPattern: "^$|^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([\
#       0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9])\
#       )$"
#     Default: ""
#     Description: (Optional) An IPv4 CIDR block for specifying the generated security
#       group's allowed addresses for inbound traffic.
#     Type: String
#
#   QSgCidr4:
#     AllowedPattern: "^$|^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([\
#       0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9])\
#       )$"
#     Default: ""
#     Description: (Optional) An IPv4 CIDR block for specifying the generated security
#       group's allowed addresses for inbound traffic.
#     Type: String
#
#   QWriteCacheIops:
#     AllowedValues:
#       - Use Qumulo Default
#       - 1000
#       - 2000
#       - 3000
#       - 4000
#       - 5000
#       - 6000
#       - 7000
#       - 8000
#       - 9000
#       - 10000
#       - 11000
#       - 12000
#       - 13000
#       - 14000
#       - 15000
#       - 16000
#     Default: Use Qumulo Default
#     Description: "Use Qumulo Default is recommended.  Applicable to io2 or gp3.
#       Minimum of 3000 for gp3."
#     Type: String
#
#   QWriteCacheTput:
#     AllowedValues:
#       - Use Qumulo Default
#       - 125
#       - 250
#       - 500
#       - 750
#       - 1000
#     Default: Use Qumulo Default
#     Description: "Use Qumulo Default is recommended.  Only applicable for gp3."
#     Type: String
#
#   QWriteCacheType:
#     AllowedValues:
#       - gp2
#       - gp3
#       - io2
#     Default: gp3
#     Description: "Choose the EBS write cache type: gp2, gp3, or io2.  Default is gp3."
#     Type: String
#
#   TermProtection:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Default: "YES"
#     Description: Enable termination protection for EC2 instances and the CloudFormation stack.
#     Type: String
#
#   VPCId:
#     Description: ID of the VPC that you're deploying this Quick Start into.
#     Type: AWS::EC2::VPC::Id
#
#   VolumesEncryptionKey:
#     Default: ""
#     Description: "(Optional) Leave blank, and AWS generates a key. To specify a
#       customer managed key (CMK), provide the KMS CMK ID in this format:
#       12345678-1234-1234-1234-1234567890ab"
#     Type: String
#
#
# Conditions:
#
#   UsingDefaultBucket: !Equals [!Ref QSS3BucketName, 'NEVER@-.']
#
#   ProvFQDN: !Not
#     - !Equals
#       - !Ref QFQDN
#       - ""
#
#   ProvNlb: !Not
#     - !Equals
#       - !Ref QNlb
#       - "NO"
#
#   ProvMultiAZ: !Not
#     - !Equals
#       - !Ref NumberAZs
#       - "1"
#
#   NlbRequired: !Or [Condition: ProvNlb, Condition: ProvMultiAZ]
#
#   ProvFloatIP: !And
#     - !Not [!Equals [!Ref QNodeCount, "1"]]
#     - !Not [Condition: ProvMultiAZ]
#
#   ProvReplacement: !Equals [!Ref QReplacementCluster, "YES"]
#
#   ProvR53: !Not [!Or [Condition: ProvReplacement, Condition: NlbRequired, !Not [Condition: ProvFloatIP], !Not [Condition: ProvFQDN]]]
#
# Rules:
#   SubnetsInVPCRule:
#     Assertions:
#       - Assert: !EachMemberIn
#         - !ValueOfAll
#           - "AWS::EC2::Subnet::Id"
#           - VpcId
#         - !RefAll "AWS::EC2::VPC::Id"
#         AssertDescription: "All subnets must be in the same VPC"
#
#   EnvTypeRule:
#     RuleCondition: !Not [!Equals [!Ref EnvType, "dev"]]
#     Assertions:
#       - Assert: !Not [!Or [!Equals [!Ref QInstanceType, "i4i.xlarge"], !Equals [!Ref QInstanceType, "i7i.xlarge"], !Equals [!Ref QInstanceType, "m6idn.xlarge"], !Equals [!Ref QInstanceType, "i3en.xlarge"], !Equals [!Ref QInstanceType, "i7ie.xlarge"]]]
#         AssertDescription: "i4i.xlarge, i7i.xlarge, i7ie.xlarge, i3en.xlarge, or m6idn.xlarge instance types are not supported for production environments. Choose at least a .2xlarge or switch to a dev environment type."
#
# Resources:
#
#   NewClusterSSM:
#     Type: AWS::SSM::Parameter
#     Properties:
#       Name: !Sub "/qumulo/${AWS::StackName}/new-cluster"
#       Value: "true"
#       Type: String
#
#   CNQStack:
#     Type: "AWS::CloudFormation::Stack"
#     DependsOn: NewClusterSSM
#     Properties:
#       Parameters:
#         EnvType: !Ref EnvType
#         KeyPair: !Ref KeyPair
#         NumberAZs: !Ref NumberAZs
#         PrivateSubnetIDs: !Join [", ", !Ref PrivateSubnetIDs]
#         QAmiID: !Ref QAmiID
#         QAuditLog: !Ref QAuditLog
#         QBootDriveSize: "256"
#         QBootDKVType: !Ref QBootDKVType
#         QClusterAdminPwd: !Ref QClusterAdminPwd
#         QClusterName: !Ref QClusterName
#         QClusterVersion: !Ref QClusterVersion
#         QDebianPackage: !Ref QDebianPackage
#         QExistingDeploymentStackName: !Ref QExistingDeploymentStackName
#         QFQDN: !Ref QFQDN
#         QInitialFloatingIP: !If [ProvFloatIP, "12", "0"]
#         QInstanceRecoveryTopic: "" #Do not change
#         QInstanceType: !Ref QInstanceType
#         QMinFloatingIPperNode: !Ref QMinFloatingIPperNode
#         QNlbDeregDelay: "60"
#         QNlbDeregTerm: "false"
#         QNlbPreserveIP: "true"
#         QNlbPrivateSubnetIDs: !If [ProvNlb, !Join [", ", !Ref QNlbPrivateSubnetIDs], !If [ProvMultiAZ, !Join [", ", !Ref PrivateSubnetIDs], ""]]
#         QNlbSticky: "true"
#         QNlbXzone: "false"
#         QNodeCount: !Ref QNodeCount
#         QPermissionsBoundary: !Ref QPermissionsBoundary
#         QPersistentStorageBucketPolicy: !Ref QPersistentStorageBucketPolicy
#         QPersistentStorageDeploymentStackName: !Ref QPersistentStorageDeploymentStackName
#         QPersistentStorageType: !Ref QPersistentStorageType
#         QReplacementCluster: !Ref QReplacementCluster
#         QSS3BucketName: !Ref QSS3BucketName
#         QSS3BucketRegion: !Ref QSS3BucketRegion
#         QSS3KeyPrefix: !Ref QSS3KeyPrefix
#         QSgCidr1: !Ref QSgCidr1
#         QSgCidr2: !Ref QSgCidr2
#         QSgCidr3: !Ref QSgCidr3
#         QSgCidr4: !Ref QSgCidr4
#         QTargetNodeCount: !Ref QTargetNodeCount
#         QWriteCacheIops: !Ref QWriteCacheIops
#         QWriteCacheTput: !Ref QWriteCacheTput
#         QWriteCacheType: !Ref QWriteCacheType
#         RequireIMDSv2: "YES"
#         SecondPrivateSubnetID: !Ref SecondPrivateSubnetID
#         TermProtection: !Ref TermProtection
#         TopStackName: !Ref AWS::StackName
#         VPCId: !Ref VPCId
#         VolumesEncryptionKey: !Ref VolumesEncryptionKey
#       TemplateURL:
#         !Sub
#           - https://${S3Bucket}.s3.${S3Region}.${AWS::URLSuffix}/${QSS3KeyPrefix}templates/cfn/cnq.cft.yaml
#           - S3Region: !If [UsingDefaultBucket, !Ref 'AWS::Region', !Ref QSS3BucketRegion]
#             S3Bucket: !If [UsingDefaultBucket, !Sub '${QSS3BucketName}-${AWS::Region}', !Ref QSS3BucketName]
#
# Outputs:
#   QumuloPrivateIP:
#     Description: Private IP for Qumulo Cluster Management
#     Value: !GetAtt CNQStack.Outputs.QumuloPrivateIP
#   QumuloPrivateIPs:
#     Description: List of the primary private IPs of the nodes in your Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloPrivateIPs
#   QumuloFloatingIPs:
#     Condition: ProvFloatIP
#     Description: List of the floating IPs in your Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloFloatingIPs
#   QumuloBucketNames:
#     Description: Qumulo S3 Bucket Names for persistent storage
#     Value: !GetAtt CNQStack.Outputs.QumuloBucketNames
#   QumuloNLBPrivateNFS:
#     Condition: NlbRequired
#     Description: Private NFS path to Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloNLBPrivateNFS
#   QumuloNLBPrivateSMB:
#     Condition: NlbRequired
#     Description: Private SMB UNC path to Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloNLBPrivateSMB
#   QumuloNLBPrivateURL:
#     Condition: NlbRequired
#     Description: Private URL for NLB Connected to Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloNLBPrivateURL
#   QumuloPrivateNFS:
#     Condition: ProvR53
#     Description: Private NFS path for Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloPrivateNFS
#   QumuloPrivateSMB:
#     Condition: ProvR53
#     Description: Private SMB UNC path for Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloPrivateSMB
#   QumuloPrivateURL:
#     Condition: ProvR53
#     Description: Private URL for Qumulo Cluster
#     Value: !GetAtt CNQStack.Outputs.QumuloPrivateURL
#   QumuloKnowledgeBase:
#     Description: Qumulo Knowledge Base
#     Value: !GetAtt CNQStack.Outputs.QumuloKnowledgeBase

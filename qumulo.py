import argparse
import boto3


class EnvoiStorageQumuloAwsCreateClusterCommand(EnvoiCommand):

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

        # AWS Template Configuration - Cloud.Next Existing VPC - Single AZ - Advanced v2.2
        parser.add_argument("--qs-s3-bucket-name", type=str, required=True,
                            help="Qumulo software S3 bucket name")
        parser.add_argument("--qs-s3-key-prefix", type=str, required=True,
                            help="Qumulo software S3 key prefix")
        parser.add_argument("--qs-s3-region", type=str, required=True,
                            help="Qumulo software S3 region")
        parser.add_argument("--key-pair-name", required=True,
                            help="Name of an existing EC2 KeyPair to enable SSH access to the node")
        parser.add_argument("--env-type", type=str, required=True,
                            help="Environment type")

        # AWS network configuration
        parser.add_argument("--vpc-id", required=True,
                            help="Qumulo cluster VPC ID")
        parser.add_argument("--security-group-cidr-1", default="10.0.0.0/16",
                            help="Security group CIDR 1")
        parser.add_argument("--security-group-cidr-2", default="", help="Security group CIDR 2")
        parser.add_argument("--security-group-cidr-3", default="", help="Security group CIDR 3")
        parser.add_argument("--security-group-cidr-4", default="", help="Security group CIDR 4")
        parser.add_argument("--private-subnet-id", type=str, required=True, help="Private subnet ID")
        parser.add_argument("--q-public-mgmt", default="NO", help="Qumulo public management")
        parser.add_argument("--q-public-repl", default="NO", help="Qumulo public replication")
        parser.add_argument("--public-subnet-id", type=str, help="Public subnet ID")
        parser.add_argument("--q-nlb", default="NO", help="Deploy an AWS network load balancer")
        parser.add_argument("--q-nlb-private-subnet-ids", type=str, help="AWS private subnet ID for the network load balancer")
        parser.add_argument("--domain-name", type=str, help="Domain name for a Route 53 hosted zone")
        parser.add_argument("--q-float-record-name", type=str, help="Route 53 record name for Qumulo-cluster floating IP addresses")

        # Qumulo file data platform configuration
        parser.add_argument("--q-ami-id", type=str, help="Qumulo AMI ID")
        parser.add_argument("--q-shared-ami", default="NO", help="Qumulo shared AMI")
        parser.add_argument("--q-debian-package", default="DEB", help="Debian or RPM package")
        parser.add_argument("--q-persistent-bucket-name", default="auto-create",
                            help="Qumulo S3 bucket name for persistent storage")
        parser.add_argument("--q-instance-type", default="m6idn.xlarge", help="Qumulo EC2 instance type")
        parser.add_argument("--q-node-count", default="4", help="Number of Qumulo EC2 instances")
        parser.add_argument("--q-disk-config", default="64GiB-Write-Cache", help="Write cache configuration")
        parser.add_argument("--q-write-cache-type", default="gp3", help="Write cache type")
        parser.add_argument("--q-write-cache-tput", default="Use Qumulo Default", help="Write cache throughput")
        parser.add_argument("--q-write-cache-iops", default="Use Qumulo Default", help="Write cache IOPS")
        parser.add_argument("--q-boot-dkv-type", default="gp3", help="Boot/DKV type")
        parser.add_argument("--q-cluster-version", default="3.2.0", help="Qumulo software version")
        parser.add_argument("--q-cluster-name", required=True, help="Qumulo cluster name")
        parser.add_argument("--q-cluster-admin-pwd", required=True, help="Qumulo cluster administrator password")
        parser.add_argument("--volumes-encryption-key", type=str, default="", help="EBS volumes encryption key")
        parser.add_argument("--q-permissions-boundary", default="", help="Qumulo permissions boundary policy name")
        parser.add_argument("--q-audit-log", default="NO", help="Qumulo audit-log messages to CloudWatch Logs")
        parser.add_argument("--term-protection", default="NO", help="Termination protection")
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
            'qs_s3_bucket_name': 'QSS3BucketName',
            'qs_s3_key_prefix': 'QSS3KeyPrefix',
            'qs_s3_region': 'QSS3BucketRegion',
            'key_pair_name': 'KeyPair',
            'env_type': 'EnvType',
            'vpc_id': 'VpcId',
            'security_group_cidr_1': 'QSgCidr1',
            'security_group_cidr_2': 'QSgCidr2',
            'security_group_cidr_3': 'QSgCidr3',
            'security_group_cidr_4': 'QSgCidr4',
            'private_subnet_id': 'PrivateSubnetID',
            'q_public_mgmt': 'QPublicMgmt',
            'q_public_repl': 'QPublicRepl',
            'public_subnet_id': 'PublicSubnetID',
            'q_nlb': 'QNlb',
            'q_nlb_private_subnet_ids': 'QNlbPrivateSubnetIDs',
            'domain_name': 'DomainName',
            'q_float_record_name': 'QFloatRecordName',
            'q_ami_id': 'QAmiID',
            'q_shared_ami': 'QSharedAmi',
            'q_debian_package': 'QDebianPackage',
            'q_persistent_bucket_name': 'QPersistentBucketName',
            'q_instance_type': 'QInstanceType',
            'q_node_count': 'QNodeCount',
            'q_disk_config': 'QDiskConfig',
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
# # Copyright (c) 2024 Qumulo, Inc.
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
# Description: This is the main template to spin up a Single-AZ Qumulo Cloud.Next Cluster with all options available in an existing VPC.  It calls cloudq.cft.yaml to instantiate the infrastructure. (qs-1s6n2i6af)
#
# Metadata:
#   cfn-lint:
#     config:
#       ignore_checks:
#         - W9006
#         - W9901
#         - E9902 #Unknown exception while processing rule E9902
#         - E9903 #Unknown exception while processing rule E9903
#         - E9904 #Unknown exception while processing rule E9904
#   QuickStartDocumentation:
#     EntrypointName: 'Parameters for deploying into an existing VPC with advanced parameters - Single AZ'
#     Order: '2'
#   AWS::CloudFormation::Interface:
#     ParameterGroups:
#       - Label:
#           default: AWS Template Configuration - Cloud.Next Existing VPC - Single AZ - Advanced v2.2
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
#           - PrivateSubnetID
#           - QPublicMgmt
#           - QPublicRepl
#           - PublicSubnetID
#           - QNlb
#           - QNlbPrivateSubnetIDs
#           - DomainName
#           - QFloatRecordName
#
#       - Label:
#           default: Qumulo file data platform configuration
#         Parameters:
#           - QAmiID
#           - QSharedAmi
#           - QDebianPackage
#           - QPersistentBucketName
#           - QInstanceType
#           - QNodeCount
#           - QDiskConfig
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
#       KeyPair:
#         default: "EC2 key pair"
#       EnvType:
#         default: "Environment type"
#       VPCId:
#         default: "VPC ID"
#       PrivateSubnetID:
#         default: "Private subnet ID"
#       PublicSubnetID:
#         default: "Public subnet ID"
#       QSgCidr1:
#         default: "CIDR #1 for the Qumulo security group"
#       QSgCidr2:
#         default: "CIDR #2 for the Qumulo security group"
#       QSgCidr3:
#         default: "CIDR #3 for the Qumulo security group"
#       QSgCidr4:
#         default: "CIDR #4 for the Qumulo security group"
#       QPublicMgmt:
#         default: "Qumulo public management"
#       QPublicRepl:
#         default: "Qumulo public replication"
#       QNlb:
#         default: "Deploy an AWS network load balancer"
#       QNlbPrivateSubnetIDs:
#         default: "AWS private subnet ID for the network load balancer"
#       DomainName:
#         default: "Domain name for a Route 53 hosted zone"
#       QFloatRecordName:
#         default: "Route 53 record name for Qumulo-cluster floating IP addresses"
#       QClusterName:
#         default: "Qumulo cluster name"
#       QClusterAdminPwd:
#         default: "Qumulo cluster administrator password"
#       QPersistentBucketName:
#         default: "Qumulo S3 bucket name for persistent storage"
#       QNodeCount:
#         default: "Number of Qumulo EC2 instances"
#       QDiskConfig:
#         default: "Write cache configuration"
#       QWriteCacheType:
#         default: "Write cache type"
#       QWriteCacheTput:
#         default: "Write cache throughput"
#       QWriteCacheIops:
#         default: "Write cache IOPS"
#       QBootDKVType:
#         default: "Boot/DKV type"
#       QClusterVersion:
#         default: "Qumulo software version"
#       QAmiID:
#         default: "Qumulo AMI ID"
#       QSharedAmi:
#         default: "Qumulo shared AMI"
#       QDebianPackage:
#         default: "Debian or RPM package"
#       QInstanceType:
#         default: "Qumulo EC2 instance type"
#       VolumesEncryptionKey:
#         default: "EBS volumes encryption key"
#       QPermissionsBoundary:
#         default: "Qumulo permissions boundary policy name"
#       QAuditLog:
#         default: "Qumulo audit-log messages to CloudWatch Logs"
#       TermProtection:
#         default: "Termination protection "
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
#       'Name of the S3 bucket for your copy of the CloudFormatin assets.'
#     Type: String
#
#   QSS3BucketRegion:
#     Default: us-west-2
#     Description: 'AWS Region where your bucket is hosted'
#     Type: String
#
#   QSS3KeyPrefix:
#     AllowedPattern: '^[0-9a-zA-Z-/]*$'
#     ConstraintDescription:
#       The S3 key prefix can include numbers, lowercase letters,
#       uppercase letters, hyphens (-), and forward slashes (/).
#     Default: aws-cloudformation-cloud-next/
#     Description:
#       'S3 key prefix that is used to simulate a folder for your copy of the
#       CloudFormation assets.'
#     Type: String
#
#   QPersistentBucketName:
#     AllowedPattern: '^[0-9a-zA-Z]+([0-9a-zA-Z-]*[0-9a-zA-Z])*$'
#     ConstraintDescription:
#       The bucket name can include numbers, lowercase
#       letters, uppercase letters, and hyphens (-). It cannot start or end with a
#       hyphen (-).
#     Default: "auto-create"
#     Description:
#       'Leave this as auto-create and this template will create a globally unique bucket that also is easily destroyed.  If you have unique S3 gateway permissions you may need to specify your own bucket.  The bucket MUST BE EMPTY.'
#     Type: String
#
#   KeyPair:
#     Description: Name of the key pair to be used to connect to your EC2 instances.
#     Type: AWS::EC2::KeyPair::KeyName
#     Default: mykeypair
#
#   EnvType:
#     Description: 'Choose "qa" or "prod" if you are not deploying into a development environment.'
#     AllowedValues:
#       - dev
#       - qa
#       - prod
#     Type: String
#     Default: dev
#
#   VPCId:
#     Type: AWS::EC2::VPC::Id
#     Description: ID of the VPC that you're deploying this Quick Start into.
#
#   QPublicMgmt:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Description: Choose YES to provision an Elastic IP address (public static) attached to a Network Load Balancer listening only on port 443 for Qumulo Management. Not supported in Local Zones or Outposts.
#     Type: String
#     Default: "NO"
#
#   QPublicRepl:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Description: Choose YES to enable port 3712 for replication from on-prem Qumulo systems using the Elastic IP (public static) for Qumulo management. Requires YES to QPublicMgmt.
#     Type: String
#     Default: "NO"
#
#   PublicSubnetID:
#     Type: AWS::EC2::Subnet::Id
#     Description: A subnet ID must be selected. It is used only if YES was selected for QPublicMgmt.
#
#   PrivateSubnetID:
#     Type: AWS::EC2::Subnet::Id
#     Description: ID of the private subnet.
#
#   QNlbPrivateSubnetIDs:
#     Type: AWS::EC2::Subnet::Id
#     Description: A subnet ID must be selected. It is used only if YES was selected for QNlb.
#
#   QNlb:
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Description: Choose YES to deploy an NLB. This will negate any Route53 PHZ options below and disable floating IPs on the cluster.
#     Type: String
#     Default: "NO"
#
#   DomainName:
#     Description: "(Optional) To create a Route 53 private hosted zone to resolve IP addresses, enter a fully qualified domain name (FQDN). You may use the .local suffix, e.g., qumulo.companyname.local. If your VPC already has a means of DNS resolution and you do not need to create a Route 53 hosted zone, keep this value blank."
#     AllowedPattern: '^$|^([a-zA-Z0-9-]+\..+)$'
#     MaxLength: '255'
#     Type: String
#     Default: ""
#
#   QFloatRecordName:
#     Description: "(Optional) Applies only if you provided DomainName. Specify a Route 53 record name for Qumulo-cluster floating IP addresses. This adds a prefix to the FQDN, e.g., cluster1.qumulo.mycompanyname.local"
#     Type: String
#     Default: ""
#
#   QNodeCount:
#     Description: "Total number of EC2 instances, or nodes, in the Qumulo cluster (4-20). You can use this field to add nodes with a CloudFormation stack update after initial provisioning."
#     AllowedValues:
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
#     Type: String
#     Default: "4"
#
#   QDiskConfig:
#     Description: "Choose the EBS volume configuration for the write cache."
#     AllowedValues:
#       - 32GiB-Write-Cache
#       - 64GiB-Write-Cache
#       - 128GiB-Write-Cache
#       - 432GiB-Write-Cache
#     Type: String
#     Default: 64GiB-Write-Cache
#
#   QWriteCacheType:
#     Description: "Choose the EBS write cache type: gp2, gp3, or io2.  Default is gp3."
#     AllowedValues:
#       - gp2
#       - gp3
#       - io2
#     Type: String
#     Default: gp3
#
#   QWriteCacheTput:
#     Description: "Use Qumulo Default is recommended.  Only applicable for gp3."
#     AllowedValues:
#       - Use Qumulo Default
#       - 125
#       - 250
#       - 500
#       - 750
#       - 1000
#     Type: String
#     Default: Use Qumulo Default
#
#   QWriteCacheIops:
#     Description: "Use Qumulo Default is recommended.  Applicable to io2 or gp3. Minimum of 3000 for gp3."
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
#     Type: String
#     Default: Use Qumulo Default
#
#   QBootDKVType:
#     Description: "Choose the EBS Boot Drive and DKV type: gp2 or gp3.  Default is gp3."
#     AllowedValues:
#       - gp2
#       - gp3
#     Type: String
#     Default: gp3
#
#   QAmiID:
#     Description: "Amazon Machine Image (AMI) ID shared by Qumulo Engineering OR is an Ubuntu AMI ID (deb) or RHL (rpm).  Leave it as Ubuntu Lookup if you don't have an AMI to specify."
#     Type: String
#     Default: Ubuntu-Lookup
#
#   QSharedAmi:
#     Description: "Yes if the AMI ID is shared from Qumulo.  Otherwise No."
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Type: String
#     Default: "NO"
#
#   QDebianPackage:
#     Description: "Debian or RPM Qumulo Core package to install."
#     AllowedValues:
#       - "DEB"
#       - "RPM"
#     Type: String
#     Default: "DEB"
#
#   QClusterName:
#     AllowedPattern: "^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$"
#     Description: Alphanumeric string between 2 and 15 characters. Dash (-) is allowed if not the first or last character.
#     MaxLength: 15
#     MinLength: 2
#     Type: String
#     Default: Cloud-Next
#
#   QClusterVersion:
#     Description: "This selects the folder within the 'qumulo-core-install' directory like: 'QSS3BucketName'/'QSS3BucketPrefix'/qumulo-core-install/'QClusterVersion'. Only applicable for package installs."
#     MaxLength: 11
#     MinLength: 5
#     Type: String
#     Default: "7.1.0"
#
#   QClusterAdminPwd:
#     AllowedPattern: "^(?=.*[a-z])(?=.*[A-Z])(?=.*[@$!%*?&\\-_])[A-Za-z\\d@$!%*?&\\-_]{8,}$"
#     Description: "Minimum 8 characters. Must include one each of the following: uppercase letter, lowercase letter, and special character."
#     MaxLength: 128
#     MinLength: 8
#     Type: String
#     NoEcho: "true"
#
#   QInstanceType:
#     Description: EC2 instance type for Qumulo nodes.
#     AllowedValues:
#       - m6idn.xlarge
#       - m6idn.2xlarge
#       - m6idn.4xlarge
#       - m6idn.8xlarge
#       - m6idn.12xlarge
#       - m6idn.16xlarge
#       - m6idn.24xlarge
#       - m6idn.32xlarge
#       - i4i.xlarge
#       - i4i.2xlarge
#       - i4i.4xlarge
#       - i4i.8xlarge
#       - i4i.12xlarge
#       - i4i.16xlarge
#       - i4i.24xlarge
#       - i4i.32xlarge
#       - i3en.xlarge
#       - i3en.2xlarge
#       - i3en.3xlarge
#       - i3en.6xlarge
#       - i3en.12xlarge
#       - i3en.24xlarge
#     Type: String
#     Default: i4i.8xlarge
#
#   VolumesEncryptionKey:
#     Description: "(Optional) Leave blank, and AWS generates a key. To specify a customer managed key (CMK), provide the KMS CMK ID in this format: 12345678-1234-1234-1234-1234567890ab"
#     Type: String
#     Default: ""
#
#   QPermissionsBoundary:
#     Description: "(Optional) Apply an IAM permissions boundary policy to the Qumulo IAM roles that are created for the Qumulo cluster and provisioning instance. This is an account-based policy.
#                   Qumulo's IAM roles conform to the least-privilege model."
#     Type: String
#     Default: ""
#
#   QSgCidr1:
#     AllowedPattern: "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9]))$"
#     Description: An IPv4 CIDR block for specifying the generated security group's allowed addresses for inbound traffic. Typically set to the VPC CIDR.
#     Type: String
#     Default: "10.0.0.0/16"
#
#   QSgCidr2:
#     AllowedPattern: "^$|^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9]))$"
#     Description: (Optional) An IPv4 CIDR block for specifying the generated security group's allowed addresses for inbound traffic.
#     Type: String
#     Default: ""
#
#   QSgCidr3:
#     AllowedPattern: "^$|^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9]))$"
#     Description: (Optional) An IPv4 CIDR block for specifying the generated security group's allowed addresses for inbound traffic.
#     Type: String
#     Default: ""
#
#   QSgCidr4:
#     AllowedPattern: "^$|^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\\/(3[0-2]|[1-2][0-9]|[0-9]))$"
#     Description: (Optional) An IPv4 CIDR block for specifying the generated security group's allowed addresses for inbound traffic.
#     Type: String
#     Default: ""
#
#   TermProtection:
#     Description: Enable termination protection for EC2 instances and the CloudFormation stack.
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Type: String
#     Default: "NO"
#
#   QAuditLog:
#     Description: Choose YES to create a CloudWatch Logs group for the Qumulo cluster that captures all Qumulo audit-log activity.
#     AllowedValues:
#       - "YES"
#       - "NO"
#     Type: String
#     Default: "NO"
#
# Conditions:
#
#   UsingDefaultBucket: !Equals [!Ref QSS3BucketName, 'NEVER@-.']
#
#   R53: !Not
#     - !Equals
#       - !Ref DomainName
#       - ""
#
#   PubMgmt: !Not
#     - !Equals
#       - !Ref QPublicMgmt
#       - "NO"
#
# #  LocalAZ: !Not
# #    - !Equals
# #      - !Ref QClusterLocalZone
# #      - "NO"
#
#   NLB: !Not
#     - !Equals
#       - !Ref QNlb
#       - "NO"
#
# #  ProvMgmt: !And [Condition: PubMgmt, !Not [Condition: LocalAZ]]
#
# #  ProvNlb: !And [Condition: NLB, !Not [Condition: LocalAZ]]
#
#   ProvMgmt: !And [Condition: PubMgmt, !Not [Condition: PubMgmt]]
#
#   ProvNlb: !Or [Condition: NLB, Condition: NLB]
#
#   ProvR53: !And [Condition: R53, !Not [Condition: NLB]]
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
# #  SubnetsInAZRuleMgmt:
# #    RuleCondition: !And [!Equals [!Ref QClusterLocalZone, "NO"], !Equals [ !Ref QPublicMgmt, "YES"]]
# #    Assertions:
# #      - Assert: !Equals
# #        - !ValueOf
# #          - PrivateSubnetID
# #          - AvailabilityZone
# #        - !ValueOf
# #          - PublicSubnetID
# #          - AvailabilityZone
# #        AssertDescription: "All subnets must be in the same Availability Zone when selecting the Public Management Option"
# #
# #  SubnetsInAZRuleNlb:
# #    RuleCondition: !And [!Equals [!Ref QClusterLocalZone, "NO"], !Equals [ !Ref QNlb, "YES"]]
# #    Assertions:
# #      - Assert: !Equals
# #        - !ValueOf
# #          - PrivateSubnetID
# #          - AvailabilityZone
# #        - !ValueOf
# #          - QNlbPrivateSubnetIDs
# #          - AvailabilityZone
# #        AssertDescription: "All subnets must be in the same Availability Zone when selecting the Network Load Balancer Deployment Option"
#
#   EnvTypeRule:
#     RuleCondition: !Not [!Equals [!Ref EnvType, "dev"]]
#     Assertions:
#       - Assert: !Not [!Or [!Equals [!Ref QInstanceType, i4i.xlarge], !Equals [!Ref QInstanceType, m6idn.xlarge], !Equals [!Ref QInstanceType, i3en.xlarge]]]
#         AssertDescription: "i4i.xlarge, i3en.xlarge, or m6idn.xlarge instance types are not supported for production environments. Choose at least a .2xlarge or switch to a dev environment type."
#
# Resources:
#
#   CloudQStack:
#     Type: "AWS::CloudFormation::Stack"
#     Properties:
#       Parameters:
#         DomainName: !If [ProvNlb, "", !Ref DomainName]
#         EnvType: !Ref EnvType
#         KeyPair: !Ref KeyPair
#         NumberAZs: "1"
#         PrivateSubnetIDs: !Ref PrivateSubnetID
#         PublicSubnetIDs: !Ref PublicSubnetID
#         QAmiID: !Ref QAmiID
#         QAmiVer: "7.1.0"
#         QAuditLog: !Ref QAuditLog
#         QBootDriveSize: "60"
#         QBootDKVType: !Ref QBootDKVType
#         QClusterAdminPwd: !Ref QClusterAdminPwd
#         QClusterLocalZone: "NO" #Do not change
#         QClusterName: !Ref QClusterName
#         QClusterVersion: !Ref QClusterVersion
#         QDebianPackage: !Ref QDebianPackage
#         QDiskConfig: !Ref QDiskConfig
#         QDr: "NO" #Do not change
#         QFloatRecordName: !If [ProvNlb, "", !Ref QFloatRecordName]
#         QFloatingIP: "0"
#         QInstanceRecoveryTopic: "" #Do not change
#         QInstanceType: !Ref QInstanceType
#         QMarketPlaceType: "Specified-AMI-ID" #Do not change
#         QMaxNodesDown: "1"
#         QModOverness: "NO"
#         QNlbDeregDelay: "60"
#         QNlbDeregTerm: "false"
#         QNlbPreserveIP: "true"
#         QNlbPrivateSubnetIDs: !If [ProvNlb, !Ref QNlbPrivateSubnetIDs, ""]
#         QNlbSticky: "true"
#         QNlbXzone: "false"
#         QNodeCount: !Ref QNodeCount
#         QPermissionsBoundary: !Ref QPermissionsBoundary
#         QPersistentBucketName: !Ref QPersistentBucketName
#         QPublicMgmt: !Ref QPublicMgmt
#         QPublicRepl: !Ref QPublicRepl
#         QSharedAmi: !Ref QSharedAmi
#         QSS3BucketName: !Ref QSS3BucketName
#         QSS3BucketRegion: !Ref QSS3BucketRegion
#         QSS3KeyPrefix: !Ref QSS3KeyPrefix
#         QSgCidr1: !Ref QSgCidr1
#         QSgCidr2: !Ref QSgCidr2
#         QSgCidr3: !Ref QSgCidr3
#         QSgCidr4: !Ref QSgCidr4
#         QWriteCacheIops: !Ref QWriteCacheIops
#         QWriteCacheTput: !Ref QWriteCacheTput
#         QWriteCacheType: !Ref QWriteCacheType
#         RequireIMDSv2: "YES"
#         SideCarPassword: !Ref QClusterAdminPwd
#         SideCarPrivateSubnetID: !Ref PrivateSubnetID #Do not change
#         SideCarProv: "NO" #Do not change
#         SideCarSNSTopic: "" #Do not change
#         SideCarUsername: "SideCarUser"
#         SideCarVersion: "7.1.0"
#         TermProtection: !Ref TermProtection
#         TopStackName: !Ref AWS::StackName
#         VPCId: !Ref VPCId
#         VolumesEncryptionKey: !Ref VolumesEncryptionKey
#       TemplateURL:
#         !Sub
#           - https://${S3Bucket}.s3.${S3Region}.${AWS::URLSuffix}/${QSS3KeyPrefix}templates/cfn/cloudq.cft.yaml
#           - S3Region: !If [UsingDefaultBucket, !Ref 'AWS::Region', !Ref QSS3BucketRegion]
#             S3Bucket: !If [UsingDefaultBucket, !Sub '${QSS3BucketName}-${AWS::Region}', !Ref QSS3BucketName]
#
# Outputs:
#
#   QumuloPrivateIP:
#     Description: Private IP for Qumulo Cluster Management
#     Value: !GetAtt CloudQStack.Outputs.QumuloPrivateIP
#   QumuloPrivateIPs:
#     Description: List of the primary private IPs of the nodes in your Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloPrivateIPs
#   QumuloBucketURI:
#     Description: Qumulo S3 Bucket for persistent storage
#     Value: !GetAtt CloudQStack.Outputs.QumuloBucketURI
#   QumuloNLBPublicURL:
#     Condition: ProvMgmt
#     Description: Public URL for Management NLB connected to Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloNLBPublicURL
#   QumuloNLBPrivateNFS:
#     Condition: ProvNlb
#     Description: Private NFS path to Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloNLBPrivateNFS
#   QumuloNLBPrivateSMB:
#     Condition: ProvNlb
#     Description: Private SMB UNC path to Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloNLBPrivateSMB
#   QumuloNLBPrivateURL:
#     Condition: ProvNlb
#     Description: Private URL for NLB Connected to Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloNLBPrivateURL
#   QumuloPrivateNFS:
#     Condition: ProvR53
#     Description: Private NFS path for Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloPrivateNFS
#   QumuloPrivateSMB:
#     Condition: ProvR53
#     Description: Private SMB UNC path for Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloPrivateSMB
#   QumuloPrivateURL:
#     Condition: ProvR53
#     Description: Private URL for Qumulo Cluster
#     Value: !GetAtt CloudQStack.Outputs.QumuloPrivateURL
#   QumuloKnowledgeBase:
#     Description: Qumulo Knowledge Base
#     Value: !GetAtt CloudQStack.Outputs.QumuloKnowledgeBase
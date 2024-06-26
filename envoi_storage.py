#!/usr/bin/env python3
import argparse
import base64
import http.client
import json
import logging
import os
import sys
import urllib.parse
from types import SimpleNamespace

try:
    # noinspection PyUnresolvedReferences
    import boto3
except ImportError:
    if __name__ == '__main__':
        print("Missing dependency boto3. Try running 'pip install boto3'")
        sys.exit(1)

LOG = logging.getLogger(__name__)


def add_from_namespace_to_dict_if_not_none(source_obj, source_key, target_obj, target_key):
    if hasattr(source_obj, source_key):
        value = getattr(source_obj, source_key)
        if value is not None:
            target_obj[target_key] = value


class CustomFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):

    def _split_lines(self, text, width):
        return text.splitlines()


class AwsCloudFormationHelper:

    @classmethod
    def client_from_opts(cls, cfn_client_args=None, opts=None):
        if cfn_client_args is None:
            cfn_client_args = {}

        if opts is None:
            opts = SimpleNamespace()

        session_args = {}
        add_from_namespace_to_dict_if_not_none(opts, 'aws_profile', session_args, 'profile_name')
        add_from_namespace_to_dict_if_not_none(opts, 'aws_region', cfn_client_args, 'region_name')

        if len(session_args) != 0:
            client_parent = boto3.Session(**session_args)
        else:
            client_parent = boto3

        return client_parent.client('cloudformation', **cfn_client_args)

    @classmethod
    def create_stack(cls, stack_name, template_url, cfn_role_arn=None, template_parameters=None, client=None,
                     cfn_client_args=None):
        if client is None:
            if cfn_client_args is None:
                cfn_client_args = {}
            client = boto3.client('cloudformation', **cfn_client_args)

        cfn_create_stack_args = {
            'StackName': stack_name,
            'TemplateURL': template_url
        }

        if template_parameters is not None:
            cfn_create_stack_args['Parameters'] = template_parameters

        if cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = cfn_role_arn

        return client.create_stack(**cfn_create_stack_args)

    @classmethod
    def populate_template_parameters_from_opts(cls, template_parameters, opts, field_map):
        for opts_param_name, template_param_name in field_map.items():
            value = getattr(opts, opts_param_name, None)
            if value is not None:
                template_parameters.append({
                    "ParameterKey": template_param_name,
                    "ParameterValue": value
                })

        return template_parameters


class EnvoiArgumentParser(argparse.ArgumentParser):

    def to_dict(self):
        # noinspection PyProtectedMember
        return {a.dest: a.default for a in self._actions if isinstance(a, argparse._StoreAction)}


class WekaApiClient:
    DEFAULT_HOST = "get.weka.io"
    DEFAULT_HOST_PORT = 443
    DEFAULT_BASE_PATH = "/dist/v1"

    def __init__(self, token, host=DEFAULT_HOST, host_port=DEFAULT_HOST_PORT, base_path=DEFAULT_BASE_PATH):
        self.conn = None
        self.token = token
        self.host = host
        self.host_port = host_port
        self.base_path = base_path
        self.default_headers = {"Content-Type": "application/json"}
        self.init_auth_header()
        self.init_connection()

    def init_connection(self):
        self.conn = http.client.HTTPSConnection(self.host, self.host_port)

    def init_auth_header(self):
        encoded_token = base64.b64encode(f"{self.token}:".encode('ascii')).decode('ascii')
        self.default_headers["Authorization"] = f"Basic {encoded_token}"

    def prepare_headers(self, headers=None, default_headers=None):
        if headers is None:
            _headers = default_headers or self.default_headers
        else:
            if default_headers is None:
                default_headers = self.default_headers or {}
            _headers = {**default_headers, **headers}
        return _headers

    @classmethod
    def handle_response(cls, response):
        response_body = response.read()
        content_type, header_attribs_raw = response.getheader("Content-Type").split(";")
        header_attribs = dict(map(lambda x: x.strip().split("="), header_attribs_raw.split(",")))
        charset = header_attribs.get("charset", "utf-8")
        try:
            if content_type == 'text/plain':
                return response_body.decode(charset)
            if content_type == "application/json":
                response_as_string = response_body.decode(charset)
                return json.loads(response_as_string) if response_as_string.strip() else None
            else:
                return response_body
        except json.JSONDecodeError as e:
            LOG.error(f"Error decoding response: {e}")
            return response_body

    def get(self, endpoint, query_params=None, headers=None, default_headers=None):
        url = self.base_path + "/" + endpoint
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        self.conn.request("GET", url, headers=self.prepare_headers(headers=headers, default_headers=default_headers))
        response = self.conn.getresponse()
        return self.__class__.handle_response(response)

    def post(self, endpoint, data, query_params=None, headers=None, default_headers=None):
        url = self.base_path + "/" + endpoint
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        self.conn.request("POST", url, json.dumps(data), headers=self.prepare_headers(headers=headers,
                                                                                      default_headers=default_headers))
        response = self.conn.getresponse()
        return self.__class__.handle_response(response)

    def get_template_releases(self, page=1):
        endpoint = "release"
        query_params = {"page": page}
        return self.get(endpoint, query_params)

    def get_latest_template_release(self):
        get_template_releases_response = self.get_template_releases()
        return get_template_releases_response["objects"][0]

    def generate_cloudformation_template(self,
                                         weka_version=None,
                                         client_instance_type=None,
                                         client_instance_count=None,
                                         client_ami_id=None,
                                         backend_instance_type=None,
                                         backend_instance_count=None):
        # @see https://docs.weka.io/install/aws/weka-installation-on-aws-using-the-cloud-formation/cloudformation
        if weka_version is None or weka_version == 'latest':
            latest_release = self.get_latest_template_release()
            weka_version = latest_release["id"]

        endpoint = f'aws/cfn/{weka_version}'

        cluster = []
        if client_instance_count is not None:
            client = {
                "role": "client",
                "instance_type": client_instance_type,
                "count": client_instance_count,

            }
            if client_ami_id is not None:
                client["ami_id"] = client_ami_id
            cluster.append(client)

        if backend_instance_count is not None:
            backend = {
                "role": "backend",
                "instance_type": backend_instance_type,
                "count": backend_instance_count,
            }
            cluster.append(backend)

        data = {
            "cluster": cluster
        }

        template_response = self.post(endpoint, data)
        return template_response


class EnvoiCommand:
    command_dest = "command"
    description = ""
    subcommands = {}

    def __init__(self, opts=None, auto_exec=True):
        self.opts = opts or {}
        if auto_exec:
            self.run()

    @classmethod
    def init_parser(cls, command_name=None, parent_parsers=None, subparsers=None,
                    formatter_class=CustomFormatter):
        if subparsers is None:
            parser = EnvoiArgumentParser(description=cls.description, parents=parent_parsers or [],
                                         formatter_class=formatter_class)
        else:
            parser = subparsers.add_parser(command_name or cls.__name__.lower(), help=cls.description,
                                           parents=parent_parsers or [],
                                           formatter_class=formatter_class)
        parser.set_defaults(handler=cls)

        if cls.subcommands:
            cls.process_subcommands(parser=parser, parent_parsers=parent_parsers, subcommands=cls.subcommands)

        return parser

    @classmethod
    def process_subcommands(cls, parser, parent_parsers, subcommands, dest=None, add_subparser_args=None):
        subcommand_parsers = {}
        if add_subparser_args is None:
            add_subparser_args = {}
        if dest is not None:
            add_subparser_args['dest'] = dest
        subparsers = parser.add_subparsers(**add_subparser_args)

        for subcommand_name, subcommand_info in subcommands.items():
            if not isinstance(subcommand_info, dict):
                subcommand_info = {"handler": subcommand_info}
            subcommand_handler = subcommand_info.get("handler", None)
            if subcommand_handler is None:
                continue
            if isinstance(subcommand_handler, str):
                subcommand_handler = globals()[subcommand_handler]

            subcommand_parser = subcommand_handler.init_parser(command_name=subcommand_name,
                                                               parent_parsers=parent_parsers,
                                                               subparsers=subparsers)
            subcommand_parser.required = subcommand_info.get("required", True)
            subcommand_parsers[subcommand_name] = subcommand_parser

        return parser

    def run(self):
        pass


class EnvoiStorageHammerspaceAwsCreateClusterCommand(EnvoiCommand):
    cfn_param_names = {
        "DeploymentType": "deployment_type",
        "AnvilConfiguration": "anvil_configuration",
        "AnvilInstanceType": "anvil_instance_type",
        "DsxInstanceType": "dsx_instance_type",
        "DsxInstanceCount": "dsx_instance_count",
        "AnvilMetaDiskSize": "anvil_meta_disk_size",
        "DsxDataDiskSize": "dsx_data_disk_size",
        "DsxAddVols": "dsx_add_vols",
        "VpcId": "vpc_id",
        "AvailZone1": "avail_zone1",
        "Subnet1Id": "subnet1_id",
        "HaSubnet1Cidr": "ha_subnet1_cidr",
        "ClusterIp": "cluster_ip",
    }

    @classmethod
    def init_parser(cls, **kwargs):
        parser = super().init_parser(**kwargs)

        """Instantiates an argument parser with the given parameters."""

        # CloudFormation Specific Arguments
        parser.add_argument("--template-url",
                            default="https://s3-external-1.amazonaws.com/cf-templates-waavb54hs3ff-us-east-1"
                                    "/2023356joQ-template12fq1v0pwupd",
                            help="Template URL")
        parser.add_argument('--stack-name', type=str, default="Hammerspace",
                            help='Stack name.')
        parser.add_argument('--aws-region', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS region. (defaults to the value from the AWS_DEFAULT_REGION environment variable)')
        parser.add_argument('--aws-profile', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS profile. (defaults to the value from the AWS_PROFILE environment variable)')
        parser.add_argument("--cfn-role-arn",
                            type=str,
                            required=False,
                            help="The ARN for the IAM role to use for creating the CloudFormation stack")

        # CloudFormation Template Parameter Arguments
        parser.add_argument("--anvil-configuration", choices=["standalone", "cluster"],
                            default="standalone",
                            help="Anvil configuration: standalone or cluster")
        parser.add_argument("--anvil-ip-address", default="0.0.0.0",
                            help="Anvil IP address")
        parser.add_argument("--anvil-instance-type", default="m5.2xlarge",
                            help="Anvil instance type")
        parser.add_argument("--anvil-instance-disk-size", type=int, default=2000,
                            help="Anvil instance disk size (GB)")
        parser.add_argument("--deployment-type", choices=["add", "new"],
                            help="Deployment type: add or new")
        parser.add_argument("--dsx-node-instance-type", default="c5.24xlarge",
                            help="DSX node instance type")
        parser.add_argument("--dsx-node-instance-count", type=int, default=8,
                            help="DSX node instance count")
        parser.add_argument("--dsx-node-instance-disk-size", type=int, default=16384,
                            help="DSX node instance disk size (GB)")
        parser.add_argument("--dsx-node-instance-add-volumes", choices=["yes", "no"], default="yes",
                            help="Add volumes to DSX nodes")
        parser.add_argument("--cluster-vpc-id", required=False,
                            help="Cluster VPC ID")
        parser.add_argument("--cluster-availability-zone", required=False,
                            help="Cluster availability zone")
        parser.add_argument("--cluster-security-group-cidr", default="0.0.0.0/0",
                            help="Cluster security group CIDR")
        parser.add_argument("--cluster-iam-instance-profile", required=False,
                            help="Cluster IAM instance profile")
        parser.add_argument("--cluster-key-pair-name", required=False,
                            help="Cluster key pair name")
        parser.add_argument("--cluster-enable-iam-user-access", choices=["yes", "no"], default="no",
                            help="Enable IAM user access to the cluster")
        parser.add_argument("--cluster-enable-iam-user-group-id",
                            help="IAM user group ID to enable access for")
        parser.add_argument("--iam-instance-role-name")

        return parser

    def run(self, opts=None):
        if opts is None:
            opts = self.opts

        cfn_template_url = opts.get("template-url")

        template_parameters = []
        for template_param_name, arg_name in self.cfn_param_names.items():
            value = getattr(opts, arg_name)
            if value is not None:
                template_parameters.append({'ParameterKey': template_param_name, 'ParameterValue': value})

        cfn_create_stack_args = {
            'StackName': opts.stack_name,
            'Parameters': template_parameters,
            'TemplateURL': cfn_template_url,
            'Capabilities': ['CAPABILITY_IAM']
        }

        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        cfn_client_args = {}
        if opts.aws_profile is not None:
            cfn_client_args['profile_name'] = opts.aws_profile

        if opts.aws_region is not None:
            cfn_client_args['region_name'] = opts.aws_region

        client = boto3.client('cloudformation', **cfn_client_args)
        response = client.create_stack(**cfn_create_stack_args)
        return response


class EnvoiStorageHammerspaceAwsCommand(EnvoiCommand):
    subcommands = {
        'create-cluster': EnvoiStorageHammerspaceAwsCreateClusterCommand,
    }


class EnvoiStorageHammerspaceCommand(EnvoiCommand):
    subcommands = {
        'aws': EnvoiStorageHammerspaceAwsCommand,
    }


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
        parser.add_argument("--q-nlb-private-subnet-ids", type=str,
                            help="AWS private subnet ID for the network load balancer")
        parser.add_argument("--domain-name", type=str, help="Domain name for a Route 53 hosted zone")
        parser.add_argument("--q-float-record-name", type=str,
                            help="Route 53 record name for Qumulo-cluster floating IP addresses")

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


class EnvoiStorageWekaAwsCreateStackCommand(EnvoiCommand):
    @classmethod
    def init_parser(cls, **kwargs):
        parser = super().init_parser(**kwargs)

        # Weka CloudFormation Template Generation Arguments
        parser.add_argument('--token', type=str, required=True, help='API Token.')
        parser.add_argument('--template-url', type=str, required=True,
                            help='The URL to the CLoudFormation template')

        parser = cls.add_uniq_arguments(parser)
        parser = cls.add_template_param_arguments(parser, required_params_required=True)
        return parser

    @classmethod
    def add_uniq_arguments(cls, parser):
        # CloudFormation Specific Arguments
        parser.add_argument('--stack-name', type=str, default="Weka",
                            help='Stack name.')
        parser.add_argument('--aws-region', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS region. (defaults to the value from the AWS_DEFAULT_REGION environment variable)')
        parser.add_argument('--aws-profile', type=str, required=False,
                            default=argparse.SUPPRESS,
                            help='AWS profile. (defaults to the value from the AWS_PROFILE environment variable)')
        parser.add_argument('--cfn-role-arn', type=str, required=False,
                            help='IAM Role to use when creating the CloudFormation stack')
        return parser

    @classmethod
    def add_template_param_arguments(cls, parser, required_params_required=True):
        # CloudFormation Template Parameter Arguments

        # required template parameters
        parser.add_argument('--template-param-key-name', type=str, required=required_params_required,
                            default=argparse.SUPPRESS,
                            help='Subnet ID of the subnet in which the cluster will be installed. ')
        parser.add_argument('--template-param-subnet-id', type=str, required=required_params_required,
                            default=argparse.SUPPRESS,
                            help='A key with which you can connect to the new instances. ')
        parser.add_argument('--template-param-vpc-id', type=str, required=required_params_required,
                            default=argparse.SUPPRESS,
                            help='VPC ID of the VPC in which the cluster will be installed. ')

        # optional template parameters
        parser.add_argument('--template-param-admin-password', type=str, default=argparse.SUPPRESS,
                            help='Password for first "admin" user created in the cluster (default: "admin")'
                                 "\nNon-default password must contain at least 8 characters, with at least one "
                                 'uppercase letter, one lowercase letter, and one number or special character')
        parser.add_argument('--template-param-existing-s3-bucket-name', type=str, required=False,
                            help='Existing S3 bucket to attach to the filesystem created by the template.'
                                 '\nThe bucket has to be in the same region where the cluster is deployed. '
                                 '\nIf this parameter is provided, the New S3 Bucket parameter is ignored.')
        parser.add_argument('--template-param-network-topology', type=str, required=False,
                            help='If you are deploying in a private VPC without public access to the '
                                 'internet (not using NAT),'
                                 '\nyou can use either a custom proxy or a Weka VPC endpoint to access Weka services.'
                                 '\nIf you have not already created a VPC endpoint to Weka services or an S3 Gateway '
                                 'within this VPC,'
                                 '\nfollow the link to create one: '
                                 'https://console.aws.amazon.com/cloudformation/home'
                                 '#/stacks/create/review?templateURL=https://proxy-prerequisites.s3.eu-central-1'
                                 '.amazonaws.com/prerequisites.json&stackName=proxy-prerequisites')
        parser.add_argument('--template-param-new-s3-bucket-name', type=str, required=False,
                            help='New S3 bucket to create and attach to the filesystem created by the '
                                 'template. The bucket will not be deleted when the stack is destroyed.')
        parser.add_argument('--template-param-tiering-ssd-percent', type=str, required=False,
                            help='Existing S3 bucket to attach to the filesystem created by the template. '
                                 '\nThe bucket has to be in the same region where the cluster is deployed.'
                                 '\nIf this parameter is provided, the New S3 Bucket parameter is ignored.')
        parser.add_argument('--template-param-weka-volume-type', type=str, required=False,
                            help='Volume type for the Weka partition.\nGP3 is not yet available in all zones/regions '
                                 '(e.g., not available in local zones).'
                                 '\nIn such a case, you must select the GP2 volume type. '
                                 '\nWhen available, using GP3 is preferred.')

        return parser

    @classmethod
    def create_stack(cls, opts, template_url=None):
        template_parameters = [{'ParameterKey': 'DistToken', 'ParameterValue': opts.token}]

        template_parameters_to_check = {
            # Required
            'template_param_key_name': 'KeyName',
            'template_param_subnet_id': 'SubnetId',
            'template_param_vpc_id': 'VpcId',

            # Optional
            'template_param_admin_password': 'AdminPassword',
            'template_param_existing_s3_bucket_name': 'ExistingS3BucketName',
            'template_param_network_topology': 'NetworkTopology',
            'template_param_new_s3_bucket_name': 'NewS3BucketName',
            'template_param_tiering_ssd_percent': 'TieringSsdPercent'
        }

        template_parameters = AwsCloudFormationHelper.populate_template_parameters_from_opts(
            template_parameters=template_parameters,
            opts=opts,
            field_map=template_parameters_to_check)

        cfn_create_stack_args = {
            'StackName': opts.stack_name,
            'Parameters': template_parameters,
            'Capabilities': ['CAPABILITY_IAM']
        }

        if template_url is not None:
            cfn_create_stack_args['TemplateURL'] = template_url
        elif hasattr(opts, 'template_url'):
            cfn_create_stack_args['TemplateURL'] = opts.template_url
        else:
            raise ValueError("Missing required parameter template_url")

        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        client = AwsCloudFormationHelper.client_from_opts(opts=opts)

        response = client.create_stack(**cfn_create_stack_args)
        return response

    def run(self, opts=None, template_url=None):
        if opts is None:
            opts = self.opts

        response = self.__class__.create_stack(opts=opts, template_url=template_url)
        stack_id = response['StackId']
        if stack_id is not None:
            response = f"Stack ID {stack_id}"

        return response


class EnvoiStorageWekaAwsGenerateTemplateCommand(EnvoiCommand):
    @classmethod
    def init_parser(cls, **kwargs):
        parser = super().init_parser(**kwargs)

        # Weka CloudFormation Template Generation Arguments
        parser.add_argument('--token', type=str, required=True, default=argparse.SUPPRESS,
                            help='API Token.')

        return cls.add_uniq_arguments(parser)

    @classmethod
    def add_uniq_arguments(cls, parser):
        parser.add_argument('--weka-version', type=str, default='latest',
                            help='Weka version.')
        parser.add_argument('--backend-instance-count', type=int, default=6,
                            help='Backend instance count.')
        parser.add_argument('--backend-instance-type', type=str, default='i3en.2xlarge',
                            help='Backend instance type.')
        parser.add_argument('--client-instance-count', type=int, default=0,
                            help='Client instance count.')
        parser.add_argument('--client-instance-type', type=str, default='r3.xlarge',
                            help='Client instance type.')
        parser.add_argument('--client-ami-id', type=str, required=False,
                            help='Client AMI ID.')
        return parser

    @classmethod
    def generate_template(cls, opts):
        client = WekaApiClient(token=opts.token)

        generate_cloudformation_template_opts = {
            "weka_version": opts.weka_version,
            "client_instance_type": opts.client_instance_type,
            "client_instance_count": opts.client_instance_count,
            "backend_instance_type": opts.backend_instance_type,
            "backend_instance_count": opts.backend_instance_count,
        }

        generate_cloudformation_template_response = client.generate_cloudformation_template(
            **generate_cloudformation_template_opts)
        return generate_cloudformation_template_response

    def run(self, opts=None):
        if opts is None:
            opts = self.opts

        response = self.__class__.generate_template(opts=opts)

        try:
            response_to_print = json.dumps(response, indent=4, sort_keys=True, default=str)
        except TypeError:
            response_to_print = response
        print(response_to_print)

        return response


class EnvoiStorageWekaAwsCreateTemplateAndStackCommand(EnvoiCommand):
    @classmethod
    def init_parser(cls, parent_parsers=None, **kwargs):
        parser = super().init_parser(parent_parsers=parent_parsers, **kwargs)

        # Weka CloudFormation Template Generation Arguments
        parser.add_argument('--token', type=str, required=True, help='API Token.')
        parser = EnvoiStorageWekaAwsGenerateTemplateCommand.add_uniq_arguments(parser)

        parser.add_argument('--create-stack', action='store', default=True,
                            help='Triggers the Creation of the CloudFormation stack.')
        parser = EnvoiStorageWekaAwsCreateStackCommand.add_uniq_arguments(parser)
        parser = EnvoiStorageWekaAwsCreateStackCommand.add_template_param_arguments(parser,
                                                                                    required_params_required=False)
        return parser

    def run(self, opts=None):
        if opts is None:
            opts = self.opts

        generate_cloudformation_template_response = (EnvoiStorageWekaAwsGenerateTemplateCommand
                                                     .generate_template(opts=opts))

        if opts.create_stack:
            template_url = generate_cloudformation_template_response['url']
            response = EnvoiStorageWekaAwsCreateStackCommand(opts=opts, auto_exec=False).run(template_url=template_url)
        else:
            response = generate_cloudformation_template_response

        try:
            response_as_string = str(response)
            if response_as_string.startswith("{") and response_as_string.endswith("}"):
                response_to_print = json.dumps(response, indent=4, sort_keys=True, default=str)
            else:
                response_to_print = response_as_string
        except TypeError:
            response_to_print = response
        print(response_to_print)

        return response


class EnvoiStorageWekaAwsCommand(EnvoiCommand):
    subcommands = {
        'create-stack': EnvoiStorageWekaAwsCreateStackCommand,
        'create-template': EnvoiStorageWekaAwsGenerateTemplateCommand,
        'create-template-and-stack': EnvoiStorageWekaAwsCreateTemplateAndStackCommand,
    }


class EnvoiStorageWekaCommand(EnvoiCommand):
    subcommands = {
        'aws': EnvoiStorageWekaAwsCommand,
    }


class EnvoiCommandLineUtility(EnvoiCommand):

    @classmethod
    def parse_command_line(cls, cli_args, env_vars, subcommands=None):
        parent_parser = EnvoiArgumentParser(add_help=False)
        parent_parser.add_argument("--log-level", dest="log_level", default="WARNING",
                                   help="Set the logging level (options: DEBUG, INFO, WARNING, ERROR, CRITICAL)")

        # main parser
        parser = EnvoiArgumentParser(description='Envoi Storage Command Line Utility', parents=[parent_parser])

        if subcommands is not None:
            subcommand_parsers = {}
            subparsers = parser.add_subparsers(dest='command')
            subparsers.required = True

            for subcommand_name, subcommand_handler in subcommands.items():
                if subcommand_handler is None:
                    continue
                subcommand_parser = subcommand_handler.init_parser(command_name=subcommand_name,
                                                                   parent_parsers=[parent_parser],
                                                                   subparsers=subparsers)
                subcommand_parser.required = True
                subcommand_parsers[subcommand_name] = subcommand_parser

        (opts, unknown_args) = parser.parse_known_args(cli_args)
        return opts, unknown_args, env_vars, parser

    @classmethod
    def handle_cli_execution(cls):
        """
        Handles the execution of the command-line interface (CLI) for the application.

        :returns: Returns 0 if successful, 1 otherwise.
        """
        cli_args = sys.argv[1:]
        env_vars = os.environ.copy()

        subcommands = {
            "hammerspace": EnvoiStorageHammerspaceCommand,
            "qumulo": EnvoiStorageQumuloCommand,
            "weka": EnvoiStorageWekaCommand,
        }

        opts, _unhandled_args, env_vars, parser = cls.parse_command_line(cli_args, env_vars, subcommands)

        ch = logging.StreamHandler()
        ch.setLevel(opts.log_level.upper())
        LOG.addHandler(ch)

        try:
            # If 'handler' is in args, run the correct handler
            if hasattr(opts, 'handler'):
                opts.handler(opts)
            else:
                parser.print_help()
                return 1

            return 0
        except Exception as e:
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.exception(e)  # Log full exception with stack trace in debug mode
            else:
                LOG.error(e.args if hasattr(e, 'args') else e)  # Log only the error message in non-debug mode
            return 1


def lambda_run_command(command, args):
    # Normalize the input to mimic the argparse output.
    parser = command.init_parser()
    opts_dict = parser.to_dict()
    opts_dict.update(args)
    print('Opts:', opts_dict)
    opts = SimpleNamespace(**opts_dict)

    response = command(opts, auto_exec=False).run()
    response_type = type(response)
    print("Response Type", response_type)
    print("Response", response)

    return response


def lambda_get_command_info_from_event(event):
    """
    Determine the command and its arguments from the given event.

    :param event: The event object containing the command details.
    :return: A tuple containing the command and its arguments.

    :raises ValueError: If the event source is unhandled.

    note:: The `event` parameter should be a dictionary object.

    """
    command_name = os.getenv('COMMAND_NAME', 'EnvoiStorageWekaAwsCommand')
    command = globals()[command_name]
    if 'eventSourceArn' in event:
        event_source_arn = event['eventSourceArn']
        if 'body' in event:
            command_args = json.loads(event['body'])
        else:
            raise ValueError(f"Unhandled event source: {event_source_arn}")
            # records = event['Records']
            # record = records[0]
    else:
        command_args = event

    return command, command_args


def lambda_handler(event, _context):
    print("Received event: " + json.dumps(event, indent=2))
    command, command_args = lambda_get_command_info_from_event(event)
    return lambda_run_command(command, command_args)


if __name__ == '__main__':
    EXIT_CODE = EnvoiCommandLineUtility.handle_cli_execution()
    sys.exit(EXIT_CODE)

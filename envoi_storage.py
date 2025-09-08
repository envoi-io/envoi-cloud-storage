#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This shebang line and encoding declaration specify the interpreter and encoding for the script.

import argparse
# Used to parse command-line arguments.
import base64
# For encoding API tokens in Base64 for HTTP authentication.
import http.client
# A low-level client for making HTTP requests, used by the WekaApiClient.
import json
# For handling JSON data, specifically parsing API responses and formatting request bodies.
import logging
# A standard library for logging messages and debugging.
import os
# Provides a way of using operating system dependent functionality, though not extensively used here.
import sys
# Provides access to system-specific parameters and functions, used for handling missing dependencies.
import urllib.parse
# For encoding URL query parameters.
from types import SimpleNamespace
# A class to create objects with a namespace for attributes, used to store parsed arguments.

try:
    # noinspection PyUnresolvedReferences
    import boto3
# This is the AWS SDK for Python, essential for interacting with AWS services like CloudFormation.
except ImportError:
    if __name__ == '__main__':
        # Checks if the script is being run directly.
        print("Missing dependency boto3. Try running 'pip install boto3'")
        sys.exit(1)
    # The script exits with an error if the boto3 library is not installed.

LOG = logging.getLogger(__name__)
# Initializes a logger object for the current module.


def add_from_namespace_to_dict_if_not_none(source_obj, source_key, target_obj, target_key):
    # This helper function checks if an attribute exists and is not None in a source object (like the parsed arguments).
    # If it exists, it copies the value to a target dictionary with a specified key.
    if hasattr(source_obj, source_key):
        value = getattr(source_obj, source_key)
        if value is not None:
            target_obj[target_key] = value


class CustomFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    # This class customizes the help output of the argument parser.
    # It allows newlines in the help text and shows default values for arguments.

    def _split_lines(self, text, width):
        # Overrides the default line-splitting behavior to preserve newlines in help text.
        return text.splitlines()


class AwsCloudFormationHelper:
    # A utility class for interacting with the AWS CloudFormation service using boto3.

    @classmethod
    def client_from_opts(cls, cfn_client_args=None, opts=None):
        # A class method to create a CloudFormation client instance.
        # It handles optional AWS profile and region settings from the command-line options.
        if cfn_client_args is None:
            cfn_client_args = {}

        if opts is None:
            opts = SimpleNamespace()

        session_args = {}
        # Populates session arguments for boto3.Session if an AWS profile is specified.
        add_from_namespace_to_dict_if_not_none(opts, 'aws_profile', session_args, 'profile_name')
        # Populates client arguments if an AWS region is specified.
        add_from_namespace_to_dict_if_not_none(opts, 'aws_region', cfn_client_args, 'region_name')

        if len(session_args) != 0:
            client_parent = boto3.Session(**session_args)
        else:
            client_parent = boto3

        return client_parent.client('cloudformation', **cfn_client_args)

    @classmethod
    def create_stack(cls, stack_name, template_url, cfn_role_arn=None, template_parameters=None, client=None,
                     cfn_client_args=None):
        # A class method to create a CloudFormation stack.
        # It takes the stack name, template URL, and optional parameters and role ARN.
        if client is None:
            if cfn_client_args is None:
                cfn_client_args = {}
            client = boto3.client('cloudformation', **cfn_client_args)

        cfn_create_stack_args = {
            'StackName': stack_name,
            'TemplateURL': template_url
        }

        # Adds optional parameters and role ARN to the stack creation arguments.
        if template_parameters is not None:
            cfn_create_stack_args['Parameters'] = template_parameters

        if cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = cfn_role_arn

        # Calls the boto3 create_stack method with the prepared arguments.
        return client.create_stack(**cfn_create_stack_args)

    @classmethod
    def populate_template_parameters_from_opts(cls, template_parameters, opts, field_map):
        # A helper method to populate a list of CloudFormation parameters from parsed command-line options.
        # It uses a field map to match option names to CloudFormation parameter names.
        for opts_param_name, template_param_name in field_map.items():
            value = getattr(opts, opts_param_name, None)
            if value is not None:
                template_parameters.append({
                    "ParameterKey": template_param_name,
                    "ParameterValue": value
                })

        return template_parameters


class EnvoiArgumentParser(argparse.ArgumentParser):
    # A custom ArgumentParser class.

    def to_dict(self):
        # A method to convert the parsed arguments into a dictionary, including default values.
        # It iterates through the parser's actions to find and store the default values.
        # noinspection PyProtectedMember
        return {a.dest: a.default for a in self._actions if isinstance(a, argparse._StoreAction)}


class WekaApiClient:
    # A client for interacting with the WekaIO API.

    DEFAULT_HOST = "get.weka.io"
    DEFAULT_HOST_PORT = 443
    DEFAULT_BASE_PATH = "/dist/v1"

    def __init__(self, token, host=DEFAULT_HOST, host_port=DEFAULT_HOST_PORT, base_path=DEFAULT_BASE_PATH):
        # Initializes the API client with a token and optional host/port.
        self.conn = None
        self.token = token
        self.host = host
        self.host_port = host_port
        self.base_path = base_path
        self.default_headers = {"Content-Type": "application/json"}
        self.init_auth_header()
        self.init_connection()

    def init_connection(self):
        # Initializes an HTTPS connection to the WekaIO API host.
        self.conn = http.client.HTTPSConnection(self.host, self.host_port)

    def init_auth_header(self):
        # Prepares the HTTP Authorization header using the provided token.
        encoded_token = base64.b64encode(f"{self.token}:".encode('ascii')).decode('ascii')
        self.default_headers["Authorization"] = f"Basic {encoded_token}"

    def prepare_headers(self, headers=None, default_headers=None):
        # Merges default headers with any provided custom headers.
        if headers is None:
            _headers = default_headers or self.default_headers
        else:
            if default_headers is None:
                default_headers = self.default_headers or {}
            _headers = {**default_headers, **headers}
        return _headers

    @classmethod
    def handle_response(cls, response):
        # A static method to read and decode the response body from an HTTP request.
        # It handles different content types (JSON, text) and decodes them appropriately.
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
        # Sends a GET request to a specified API endpoint with optional query parameters and headers.
        url = self.base_path + "/" + endpoint
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        self.conn.request("GET", url, headers=self.prepare_headers(headers=headers, default_headers=default_headers))
        response = self.conn.getresponse()
        return self.__class__.handle_response(response)

    def post(self, endpoint, data, query_params=None, headers=None, default_headers=None):
        # Sends a POST request with JSON data to a specified API endpoint.
        url = self.base_path + "/" + endpoint
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        self.conn.request("POST", url, json.dumps(data), headers=self.prepare_headers(headers=headers,
                                                                                      default_headers=default_headers))
        response = self.conn.getresponse()
        return self.__class__.handle_response(response)

    def get_template_releases(self, page=1):
        # Retrieves a list of available WekaIO template releases.
        endpoint = "release"
        query_params = {"page": page}
        return self.get(endpoint, query_params)

    def get_latest_template_release(self):
        # Fetches and returns the latest available WekaIO template release.
        get_template_releases_response = self.get_template_releases()
        return get_template_releases_response["objects"][0]

    def generate_cloudformation_template(self,
                                         weka_version=None,
                                         client_instance_type=None,
                                         client_instance_count=None,
                                         client_ami_id=None,
                                         backend_instance_type=None,
                                         backend_instance_count=None):
        # This method generates a WekaIO CloudFormation template by making a POST request to the API.
        # It constructs the request body based on the provided instance and version details.
        if weka_version is None or weka_version == 'latest':
            latest_release = self.get_latest_template_release()
            weka_version = latest_release["id"]

        endpoint = f'aws/cfn/{weka_version}'

        cluster = []
        # Adds client and backend cluster information to the request data if counts are provided.
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

        # Sends the POST request to the API to generate the template.
        template_response = self.post(endpoint, data)
        return template_response


class EnvoiCommand:
    # A base class for all commands.

    command_dest = "command"
    description = ""
    subcommands = {}

    def __init__(self, opts=None, auto_exec=True):
        # Initializes the command with parsed options. It can be set to run automatically.
        self.opts = opts or {}
        if auto_exec:
            self.run()

    @classmethod
    def init_parser(cls, command_name=None, parent_parsers=None, subparsers=None,
                    formatter_class=CustomFormatter):
        # A class method to initialize an argument parser for a specific command.
        # It handles setting up subparsers for nested commands.
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
        # A method to recursively process and set up subparsers for nested commands.
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
        # A placeholder method that must be implemented by child classes to define the command's behavior.
        pass


class EnvoiStorageHammerspaceAwsCreateClusterCommand(EnvoiCommand):
    # A command class for creating a Hammerspace cluster on AWS.

    cfn_param_names = {
        # A dictionary mapping command-line argument names to CloudFormation parameter names.
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
        # Initializes the argument parser specifically for the Hammerspace `create-cluster` command.
        # It defines arguments for CloudFormation settings and Hammerspace-specific template parameters.
        parser = super().init_parser(**kwargs)

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
        # The following lines define the arguments that correspond to parameters in the CloudFormation template.
        # This includes instance types, disk sizes, VPC details, etc.
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
        # The main execution method for the command.
        # It prepares the CloudFormation stack creation parameters and calls the boto3 client.
        if opts is None:
            opts = self.opts

        cfn_template_url = opts.get("template-url")

        template_parameters = []
        # Populates the CloudFormation template parameters from the parsed options.
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

        # Adds the optional IAM role ARN to the arguments.
        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        # Prepares the boto3 client with the correct profile and region.
        cfn_client_args = {}
        if opts.aws_profile is not None:
            cfn_client_args['profile_name'] = opts.aws_profile

        if opts.aws_region is not None:
            cfn_client_args['region_name'] = opts.aws_region

        client = boto3.client('cloudformation', **cfn_client_args)
        response = client.create_stack(**cfn_create_stack_args)
        return response


class EnvoiStorageHammerspaceAwsCommand(EnvoiCommand):
    # This class serves as a namespace for the Hammerspace AWS commands.
    subcommands = {
        'create-cluster': EnvoiStorageHammerspaceAwsCreateClusterCommand,
    }


class EnvoiStorageHammerspaceCommand(EnvoiCommand):
    # This class serves as a namespace for the Hammerspace commands.
    subcommands = {
        'aws': EnvoiStorageHammerspaceAwsCommand,
    }


class EnvoiStorageQumuloAwsCreateClusterCommand(EnvoiCommand):
    # This command class handles the creation of a Qumulo cluster on AWS.
    # It defines a comprehensive set of arguments for configuring the Qumulo CloudFormation template.

    @classmethod
    def init_parser(cls, parent_parsers=None, **kwargs):
        parser = super().init_parser(parent_parsers=parent_parsers, **kwargs)
        # Defines arguments for the Qumulo cluster, including template URL, stack name, and AWS settings.
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

        # Defines arguments for the CloudFormation template parameters specific to Qumulo.
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

        # Arguments for AWS network configuration.
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

        # Arguments for Qumulo file data platform configuration.
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
        # The main execution method for the Qumulo command.
        if opts is None:
            opts = self.opts
        cfn_client_args = {}
        # Populates the CloudFormation client arguments from the command-line options.
        add_from_namespace_to_dict_if_not_none(opts, 'aws_profile', cfn_client_args, 'profile_name')
        add_from_namespace_to_dict_if_not_none(opts, 'aws_region', cfn_client_args, 'region_name')

        client = boto3.client('cloudformation', **cfn_client_args)
        template_parameters = []

        template_parameters_to_check = {
            # This dictionary maps command-line arguments to the corresponding CloudFormation parameter names.
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

        # Iterates through the mapping and adds parameters to the list if their corresponding argument exists.
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

        # Ensures the template URL is provided before creating the stack.
        if hasattr(opts, 'template_url'):
            cfn_create_stack_args['TemplateURL'] = opts.template_url
        else:
            raise ValueError("Missing required parameter template_url")

        # Adds the optional CloudFormation role ARN.
        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        response = client.create_stack(**cfn_create_stack_args)
        stack_id = response['StackId']
        # Returns the stack ID if the creation request is successful.
        if stack_id is not None:
            response = f"Stack ID {stack_id}"

        return response


class EnvoiStorageQumuloLegacyAwsCreateClusterCommand(EnvoiCommand):
    # A legacy command for creating a Qumulo cluster on AWS with a simpler set of arguments.
    # It demonstrates how different versions or configurations can be handled with separate classes.

    @classmethod
    def init_parser(cls, parent_parsers=None, **kwargs):
        # Defines the argument parser for the legacy Qumulo command.
        parser = super().init_parser(parent_parsers=parent_parsers, **kwargs)
        # It includes a more basic set of parameters compared to the newer Qumulo command.
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

        # Optional arguments with default values.
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
        # Execution method for the legacy Qumulo command, which is very similar to the main Qumulo command's logic.
        if opts is None:
            opts = self.opts
        cfn_client_args = {}
        add_from_namespace_to_dict_if_not_none(opts, 'aws_profile', cfn_client_args, 'profile_name')
        add_from_namespace_to_dict_if_not_none(opts, 'aws_region', cfn_client_args, 'region_name')

        client = boto3.client('cloudformation', **cfn_client_args)
        template_parameters = []

        template_parameters_to_check = {
            # Maps legacy argument names to CloudFormation parameter names.
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
    # Namespace class for Qumulo AWS commands.
    subcommands = {
        'create-cluster': EnvoiStorageQumuloAwsCreateClusterCommand,
    }


class EnvoiStorageQumuloCommand(EnvoiCommand):
    # Namespace class for Qumulo commands.
    subcommands = {
        'aws': EnvoiStorageQumuloAwsCommand,
    }


class EnvoiStorageWekaAwsCreateStackCommand(EnvoiCommand):
    # This class handles the creation of a WekaIO stack on AWS.
    # It's unique because it first uses the Weka API to dynamically generate a CloudFormation template.

    @classmethod
    def init_parser(cls, **kwargs):
        # Initializes the parser for the WekaIO command.
        parser = super().init_parser(**kwargs)

        # Defines arguments for Weka API token and template URL.
        parser.add_argument('--token', type=str, required=True, help='API Token.')
        parser.add_argument('--template-url', type=str, required=True,
                            help='The URL to the CLoudFormation template')

        # The following methods are used to add groups of arguments to the parser.
        parser = cls.add_uniq_arguments(parser)
        parser = cls.add_template_param_arguments(parser, required_params_required=True)
        return parser

    @classmethod
    def add_uniq_arguments(cls, parser):
        # Adds generic CloudFormation-related arguments to the parser.
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
        # Adds arguments that correspond to the WekaIO CloudFormation template parameters.
        # These are crucial for configuring the WekaIO cluster.
        parser.add_argument('--template-param-key-name', type=str, required=required_params_required,
                            default=argparse.SUPPRESS,
                            help='Subnet ID of the subnet in which the cluster will be installed. ')
        parser.add_argument('--template-param-subnet-id', type=str, required=required_params_required,
                            default=argparse.SUPPRESS,
                            help='A key with which you can connect to the new instances. ')
        parser.add_argument('--template-param-vpc-id', type=str, required=required_params_required,
                            default=argparse.SUPPRESS,
                            help='VPC ID of the VPC. ')

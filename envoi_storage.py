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

logger = logging.getLogger(__name__)


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
            if content_type == 'text/plain:':
                return response_body.decode(charset)
            if content_type == "application/json":
                response_as_string = response_body.decode(charset)
                return json.loads(response_as_string) if response_as_string.strip() else None
            else:
                return response_body
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding response: {e}")
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
                                         template_version=None,
                                         client_instance_type=None,
                                         client_instance_count=None,
                                         client_ami_id=None,
                                         backend_instance_type=None,
                                         backend_instance_count=None):
        # @see https://docs.weka.io/install/aws/weka-installation-on-aws-using-the-cloud-formation/cloudformation
        if template_version is None or template_version == 'latest':
            latest_release = self.get_latest_template_release()
            template_version = latest_release["id"]

        endpoint = f'aws/cfn/{template_version}'

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
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter):
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
                            help='AWS region.')
        parser.add_argument('--aws-profile', type=str, required=False,
                            help='AWS profile.')
        parser.add_argument("--cfn-role-arn",
                            type=str,
                            required=False,
                            help="The ARN for the IAM role to use for creating the stack")

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
            'Parameters':  template_parameters,
            'TemplateURL': cfn_template_url,
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

        parser.add_argument("--name", help="Qumulo cluster name")

        # Optional arguments
        parser.add_argument("--iam-instance-profile", default="qumulo-iam-instance-role-name",
                            help="IAM instance profile name")
        parser.add_argument("--instance-type", default="c7gn.8xlarge",
                            help="Qumulo cluster instance type")
        parser.add_argument("--key-pair-name", default="qumulo-dev",
                            help="Qumulo cluster key pair name")
        parser.add_argument("--vpc-id", default="qumulo-dev-vpc-id",
                            help="Qumulo cluster VPC ID")
        parser.add_argument("--security-group-cidr", default="0.0.0.0/0",
                            help="Qumulo cluster security group CIDR")
        parser.add_argument("--kms-key", default="qumulo-dev-key",
                            help="Qumulo cluster KMS key")

        return parser


class EnvoiStorageQumuloAwsCommand(EnvoiCommand):
    subcommands = {
        'create-cluster': EnvoiStorageQumuloAwsCreateClusterCommand,
    }


class EnvoiStorageQumuloCommand(EnvoiCommand):
    subcommands = {
        'aws': EnvoiStorageQumuloAwsCommand,
    }


class EnvoiStorageWekaAwsCreateClusterCommand(EnvoiCommand):
    @classmethod
    def init_parser(cls, parent_parsers=None, **kwargs):
        parser = super().init_parser(parent_parsers=parent_parsers, **kwargs)

        # Weka CloudFormation Template Generation Arguments
        parser.add_argument('--token', type=str, required=True, help='API Token.')
        parser.add_argument('--template-version', type=str, default='latest',
                            help='Template version.')
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

        # CloudFormation Specific Arguments
        parser.add_argument('--create-stack', action='store', default=False,
                            help='Triggers the Creation of the stack.')
        parser.add_argument('--stack-name', type=str, default="Weka",
                            help='Stack name.')
        parser.add_argument('--aws-region', type=str, required=False,
                            help='AWS region.')
        parser.add_argument('--aws-profile', type=str, required=False,
                            help='AWS profile.')
        parser.add_argument('--cfn-role-arn', type=str, required=False,
                            help='IAM Role to use when creating the stack')

        # CloudFormation Template Parameter Arguments
        parser.add_argument('--template-param-admin-password', type=str, required=False,
                            help='Password for first "admin" user created in the cluster '
                                 '(default: "admin")'
                                 'Non-default password must contain at least 8 characters, with at least one '
                                 'uppercase letter, one lowercase letter, and one number or special character')
        parser.add_argument('--template-param-key-name', type=str, required=False,
                            help='[Required when creating the stack] '
                                 'Subnet ID of the subnet in which the cluster would be installed')
        parser.add_argument('--template-param-subnet-id', type=str, required=False,
                            help='[Required when creating the stack] '
                                 'A key with which you can connect to the new instances')
        parser.add_argument('--template-param-vpc-id', type=str, required=False,
                            help='[Required when creating the stack] '
                                 'VPC ID of the VPC in which the cluster would be installed')
        return parser

    def create_stack(self, opts=None, template_url=None):
        if opts is None:
            opts = self.opts

        cfn_client_args = {}
        if opts.aws_profile is not None:
            cfn_client_args['profile_name'] = opts.aws_profile

        if opts.aws_region is not None:
            cfn_client_args['region_name'] = opts.aws_region

        client = boto3.client('cloudformation', **cfn_client_args)
        template_parameters = [{'ParameterKey': 'DistToken', 'ParameterValue': opts.token}]

        template_parameters_to_check = {
            'template_param_admin_password': 'AdminPassword',
            'template_param_key_name': 'KeyName',
            'template_param_subnet_id': 'SubnetId',
            'template_param_vpc_id': 'VpcId',
        }

        for opts_param_name, template_param_name in template_parameters_to_check.items():
            if hasattr(opts, opts_param_name):
                value = getattr(opts, opts_param_name)
                if value is not None:
                    template_parameters.append({'ParameterKey': template_param_name, 'ParameterValue': value})

        cfn_create_stack_args = {
            'StackName': opts.stack_name,
            'Parameters': template_parameters
        }

        if template_url is not None:
            cfn_create_stack_args['TemplateURL'] = template_url
        elif hasattr(opts, 'cfn_template_url'):
            cfn_create_stack_args['TemplateURL'] = opts.cfn_template_url

        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        response = client.create_stack(**cfn_create_stack_args)
        return response

    def run(self, opts=None):
        if opts is None:
            opts = self.opts

        client = WekaApiClient(token=opts.token)

        generate_cloudformation_template_opts = {
            "template_version": opts.template_version,
            "client_instance_type": opts.client_instance_type,
            "client_instance_count": opts.client_instance_count,
            "backend_instance_type": opts.backend_instance_type,
            "backend_instance_count": opts.backend_instance_count,
        }

        generate_cloudformation_template_response = client.generate_cloudformation_template(
            **generate_cloudformation_template_opts)
        response = generate_cloudformation_template_response

        if opts.create_stack:
            template_url = generate_cloudformation_template_response['url']
            response = self.create_stack(opts, template_url=template_url)

        try:
            response_to_print = json.dumps(response, indent=4, sort_keys=True, default=str)
        except TypeError:
            response_to_print = response
        print(response_to_print)

        return response


class EnvoiStorageWekaAwsCommand(EnvoiCommand):
    subcommands = {
        'create-cluster': EnvoiStorageWekaAwsCreateClusterCommand,
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
        logger.addHandler(ch)

        try:
            # If 'handler' is in args, run the correct handler
            if hasattr(opts, 'handler'):
                opts.handler(opts)
            else:
                parser.print_help()
                return 1

            return 0
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(e)  # Log full exception with stack trace in debug mode
            else:
                logger.error(e.args if hasattr(e, 'args') else e)  # Log only the error message in non-debug mode
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

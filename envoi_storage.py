#!/usr/bin/env python3
import argparse
import base64
import http.client
import json
import logging
import os
import sys
import urllib.parse

try:
    import boto3
except ImportError:
    print("Missing dependency boto3. Try running 'pip install boto3'")
    sys.exit(1)

logger = logging.getLogger(__name__)


class WekaApiClient:
    DEFAULT_HOST = "get.weka.io"
    DEFAULT_HOST_PORT = 443
    DEFAULT_BASE_PATH = "/dist/v1"

    def __init__(self, token, host=DEFAULT_HOST, host_port=DEFAULT_HOST_PORT, base_path=DEFAULT_BASE_PATH):
        self.conn = None
        self.token = token
        self.headers = {"Content-Type": "application/json", "Authorization": "Basic " + self.token}
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
        self.default_headers["Authorization"] = "Basic " + encoded_token

    def prepare_headers(self, headers=None, default_headers=None):
        if headers is None:
            _headers = default_headers or self.default_headers
        else:
            if default_headers is None:
                default_headers = self.default_headers or {}
            _headers = {**default_headers, **headers}
        return _headers

    def get(self, endpoint, query_params=None, headers=None, default_headers=None):
        url = self.base_path + "/" + endpoint
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        self.conn.request("GET", url, headers=self.prepare_headers(headers=headers, default_headers=default_headers))
        response = self.conn.getresponse()
        return json.loads(response.read())

    def post(self, endpoint, data, query_params=None, headers=None, default_headers=None):
        url = self.base_path + "/" + endpoint
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)
        self.conn.request("POST", url, json.dumps(data), headers=self.prepare_headers(headers=headers,
                                                                                      default_headers=default_headers))
        response = self.conn.getresponse()
        return json.loads(response.read())

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
    DESCRIPTION = ""

    def __init__(self, opts=None, auto_exec=True):
        self.opts = opts or {}
        if auto_exec:
            self.run()

    @classmethod
    def init_parser(cls, command_name=None, parent_parsers=None, sub_parsers=None):
        if sub_parsers is None:
            parser = argparse.ArgumentParser(description=cls.DESCRIPTION, parents=parent_parsers or [])
        else:
            parser = sub_parsers.add_parser(command_name or cls.__name__.lower(), help=cls.DESCRIPTION,
                                            parents=parent_parsers or [])
        parser.set_defaults(handler=cls)
        return parser

    @classmethod
    def process_sub_commands(cls, parser, parent_parsers, sub_commands, dest=None):
        sub_command_parsers = {}
        sub_parsers = parser.add_subparsers(dest=dest)

        for sub_command_name, sub_command_handler in sub_commands.items():
            if sub_command_handler is None:
                continue
            sub_command_parser = sub_command_handler.init_parser(command_name=sub_command_name,
                                                                 parent_parsers=parent_parsers,
                                                                 sub_parsers=sub_parsers)
            sub_command_parser.required = True
            sub_command_parsers[sub_command_name] = sub_command_parser

        return parser

    def run(self):
        pass


class EnvoiStorageWekaCommand(EnvoiCommand):

    def __init__(self, opts=None, auto_exec=True):
        super().__init__(opts, auto_exec)

    @classmethod
    def init_parser(cls, command_name=None, parent_parsers=None, sub_parsers=None):
        parser = super().init_parser(command_name, parent_parsers, sub_parsers)

        sub_commands = {
            'aws': EnvoiStorageWekaAwsCommand,
        }

        if sub_commands is not None:
            cls.process_sub_commands(parser, parent_parsers, sub_commands, dest='weka_aws_command')

        return parser

    def run(self, opts=None):
        pass


class EnvoiStorageWekaAwsCommand(EnvoiCommand):

    @classmethod
    def init_parser(cls, command_name=None, parent_parsers=None, sub_parsers=None):
        parser = super().init_parser(command_name, parent_parsers, sub_parsers)

        # Weka CloudFormation Template Generation Arguments
        parser.add_argument('-t', '--token', type=str, required=True, help='Token.')
        parser.add_argument('--template_version', type=str, default='latest',
                            help='Template version.')
        parser.add_argument('-bc', '--backend-instance-count', type=int, default=6,
                            help='Backend instance count.')
        parser.add_argument('-bt', '--backend-instance-type', type=str, required=True,
                            help='Backend instance type.')
        parser.add_argument('-cc', '--client-instance-count', type=int, required=False,
                            help='Client instance count.')
        parser.add_argument('-ct', '--client-instance-type', type=str, required=False,
                            help='Client instance type.')
        parser.add_argument('-ci', '--client-ami-id', type=str, required=False,
                            help='Client AMI ID.')

        # CloudFormation Specific Arguments
        parser.add_argument('--create-stack', action='store_true', required=False,
                            help='Triggers the Creation of the stack.')
        parser.add_argument('--stack-name', type=str, default="Weka",
                            help='Stack name.')
        parser.add_argument('--aws-region', type=str, required=False,
                            help='AWS region.')
        parser.add_argument('--aws-profile', type=str, required=False,
                            help='AWS profile.')
        parser.add_argument('--cfn-role-arn', type=str, required=False,
                            help='IAM Role to use when creating the stack')

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

        cfn_create_stack_args = {
            'StackName': opts.stack_name,
            'Parameters': [{'DistToken': opts.token}]
        }

        if template_url is not None:
            cfn_create_stack_args['TemplateURL'] = template_url
        elif hasattr(opts, 'cfn_template_url'):
            cfn_create_stack_args['TemplateURL'] = opts.cfn_template_url

        if opts.cfn_role_arn is not None:
            cfn_create_stack_args['RoleARN'] = opts.cfn_role_arn

        client.create_stack(StackName=opts.stack_name, **cfn_create_stack_args)

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

        if opts.create_stack:
            template_url = generate_cloudformation_template_response['url']
            self.create_stack(opts, template_url=template_url)
        else:
            try:
                response = json.dumps(generate_cloudformation_template_response, indent=4, sort_keys=True, default=str)
            except TypeError:
                response = generate_cloudformation_template_response
            print(response)


class EnvoiCommandLineUtility:

    @classmethod
    def parse_command_line(cls, cli_args, env_vars, sub_commands=None):
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument("--log-level", dest="log_level", default="WARNING",
                                   help="Set the logging level (options: DEBUG, INFO, WARNING, ERROR, CRITICAL)")

        # main parser
        parser = argparse.ArgumentParser(description='Envoi Storage Command Line Utility', parents=[parent_parser])

        if sub_commands is not None:
            sub_command_parsers = {}
            sub_parsers = parser.add_subparsers(dest='command')
            sub_parsers.required = True

            for sub_command_name, sub_command_handler in sub_commands.items():
                if sub_command_handler is None:
                    continue
                sub_command_parser = sub_command_handler.init_parser(command_name=sub_command_name,
                                                                     parent_parsers=[parent_parser],
                                                                     sub_parsers=sub_parsers)
                sub_command_parser.required = True
                sub_command_parsers[sub_command_name] = sub_command_parser

        (opts, args) = parser.parse_known_args(cli_args)
        return opts, args, env_vars, parser

    @classmethod
    def handle_cli_execution(cls):
        """
        Handles the execution of the command-line interface (CLI) for the application.

        :returns: Returns 0 if successful, 1 otherwise.
        """
        cli_args = sys.argv[1:]
        env_vars = os.environ.copy()

        sub_commands = {
            "hammerspace": None,
            "queue": None,
            "weka": EnvoiStorageWekaCommand,
        }

        opts, _unhandled_args, env_vars, parser = cls.parse_command_line(cli_args, env_vars, sub_commands)

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
            logger.exception(e)
            return 1


def lambda_handler(event, _context):
    print("Received event: " + json.dumps(event, indent=2))

    opts = {}
    command = EnvoiStorageWekaAwsCommand(opts)

    return {"success": True}


if __name__ == '__main__':
    EXIT_CODE = EnvoiCommandLineUtility.handle_cli_execution()
    sys.exit(EXIT_CODE)

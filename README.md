# Envoi Storage

## Installation

### Prerequisites

You will need to install and configure the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)  

## Usage

### Weka

#### AWS

##### Create Weka AWS CloudFormation Template and Lauch CloudFormation Stack

This utility will automatically create a 30TB Weka Filesystem with 7.6GB/S of throughput. 

This is accomplished by leveraging the Weka API for autogenerating AWS CloudFormation 

https://docs.weka.io/install/aws/weka-installation-on-aws-using-the-cloud-formation/cloudformation

Alternatively use the create-template and create-stack sub commands to support advanced use cases.

Set AWS Environment Variable

```shell
export AWS_DEFAULT_REGION='us-east-1'
export AWS_PROFILE='AWS_PROFILE'
export WEKA_API_TOKEN='WEKA_API_TOKEN'
export KEY_NAME='KEY_NAME'
export SUBNET_ID='SUBNET_ID'
export VPC_ID='VPC_ID'
```

Example using only required arguments
```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID
--backend-instance-type i3en.6xlarge \
--backend-instance-count 6 \
--client-instance-count 2 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--log-level debug
```

Deploy Weka 30TB Filesystem with 2 clients configured with HP Anywhere CentOS 7 Linux
```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID
--backend-instance-type i3en.6xlarge \
--backend-instance-count 10 \
--client-instance-type g4dn.16xlarge \
--client-instance-count 5 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--client-ami-id "ami-08447c4aa12458688 | us-east-1, ami-08190d20c372f54cc | us-west-1 ami-0805e10141cf4a781 | us-west-2" ##Launches this CentOS 7 g5.12xlarge as a Weka client
https://aws.amazon.com/marketplace/pp/prodview-yjdn554yaqvem
```


Deploy Weka 30TB Filesystem with 2 clients configured with HP Anywhere Windows Server 2019 (NVIDIA) 
```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID
--backend-instance-type i3en.6xlarge \
--backend-instance-count 10 \
--client-instance-type g5.12xlarge \
--client-instance-count 5 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--client-ami-id "ami-08447c4aa12458688 | us-east-1, ami-08190d20c372f54cc | us-west-1 ami-0805e10141cf4a781 | us-west-2" ##Launches this CentOS 7 g5.12xlarge as a Weka client
https://aws.amazon.com/marketplace/pp/prodview-boeg6hiewus3o
```

Deploy Weka 30TB Filesystem with with 2 clients configured with HP Anywhere HP Anyware Epic Games Unreal Engine 5 on Windows 2022 Server
```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID
--backend-instance-type i3en.6xlarge \
--backend-instance-count 10 \
--client-instance-type g5.12xlarge \
--client-instance-count 5 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--client-ami-id "ami-08447c4aa12458688 | us-east-1, ami-08190d20c372f54cc | us-west-1 ami-0805e10141cf4a781 | us-west-2" ##Launches this CentOS 7 g5.12xlarge as a Weka client
https://aws.amazon.com/marketplace/pp/prodview-fryvjy6m3qn2q
```

### Qumulo

#### AWS

##### Create Cluster

```shell
qumulo aws create-cluster [-h] [--log-level LOG_LEVEL] --template-url TEMPLATE_URL --cluster-name CLUSTER_NAME --key-pair-name KEY_PAIR_NAME --vpc-id VPC_ID
                                                  --subnet-id SUBNET_ID [--iam-instance-profile-name IAM_INSTANCE_PROFILE_NAME] [--instance-type INSTANCE_TYPE]
                                                  [--security-group-cidr SECURITY_GROUP_CIDR] [--volumes-encryption-key VOLUMES_ENCRYPTION_KEY]
```

# Envoi Storage

## Installation

### Prerequisites

You will need to install and configure the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)  

## Usage

### Hammerspace

#### AWS

Set AWS Environment Variable

```shell
export AWS_DEFAULT_REGION='us-east-1'
export AWS_AVALIABILITY_ZONE='us-east-1'
export AWS_PROFILE='AWS_PROFILE'
export AWS_CLUSTER_IAM_ROLE='AWS_CLUSTER_IAM_ROLE'
export WEKA_API_TOKEN='WEKA_API_TOKEN'
export KEY_NAME='KEY_NAME'
export SUBNET_ID='SUBNET_ID'
export VPC_ID='VPC_ID'
```

##### Create Cluster

```shell
envoi-storage hammerspace aws create-cluster \
--hammerspace-deployment-type add | new \
--hammerspace-anvil-configuration standalone | cluster \
--hammerspace-anvil-ip-address 0.0.0.0 \
--hammerspace-anvil-instance-type m5.2xlarge \
--hammerspace-anvil-instance-disk-size 2000 \
--hammerspace-dsxnode-instance-type c5.24xlarge \
--hammerspace-dsxnode-instance-count 8 \
--hammerspace-dsxnode-instance-disk-size 16384 \
--hammerspace-dsxnode-instance-add-volumes yes \
--hammerspace-cluster-vpcd-id hammerspce-dev-vpc-id \
--hammerspace-cluster-availability-zone us-west-2a \
--hammerspace-cluster-security-group-cidr 0.0.0.0/0 \
--hammerspace-cluster-iam-instance-profile hammerspce-iam-instance-role-name \
--hammerspace-cluster-key-pair-name hammerspce-dev \
--hammerspace-cluster-enable-iam-user-access yes | no \
--hammerspace-cluster-enable-iam-user-group-id [iam--admin-group-id]
```

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
```

Example changing the number and type of instances
```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID \
--backend-instance-type i3en.2xlarge \
--backend-instance-count 10 \
--client-instance-type g5.12xlarge \
--client-instance-count 2
```

### Qumulo

#### AWS

##### Create Cluster

```shell
envoi-storage qumulo aws create-cluster \
--cluster-name qumulo-dev \
--iam-instance-profile qumulo-iam-instance-role-name \
--qumulo-cluster-instance-type c7gn.8xlarge \
--qumulo-cluster-key-pair-name qumulo-dev \
--qumulo-cluster-vpcd-id qumulo-dev-vpc-id \
--qumulo-cluster-security-group-cidr 0.0.0.0/0 \
--qumulo-cluster-kms-key qumulo-dev-key
```

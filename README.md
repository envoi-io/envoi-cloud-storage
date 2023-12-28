# Envoi Storage

## Installation

### Prerequisites

You will need to install and configure the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)  

## Usage

### Hammerspace

#### AWS

##### Create Cluster

```shell
envoi-storage hammerspace aws create-cluster \
--hammerspce-deployment-type add | new \
--hammerspce-anvil-configuration standalone | cluster \
--hammerspce-anvil-ip-address 0.0.0.0 \
--hammerspce-anvil-instance-type m5.2xlarge \
--hammerspce-anvil-instance-disk-size 2000 \
--hammerspce-dsxnode-instance-type c5.24xlarge \
--hammerspce-dsxnode-instance-count 8 \
--hammerspce-dsxnode-instance-disk-size 16384 \
--hammerspce-dsxnode-instance-add-volumes yes \
--hammerspce-cluster-vpcd-id hammerspce-dev-vpc-id \
--hammerspce-cluster-availability-zone us-west-2a \
--hammerspce-cluster-security-group-cidr 0.0.0.0/0 \
--hammerspce-cluster-iam-instance-profile hammerspce-iam-instance-role-name \
--hammerspce-cluster-key-pair-name hammerspce-dev \
--hammerspce-cluster-enable-iam-user-access yes | no \
--hammerspce-cluster-enable-iam-user-group-id [iam--admin-group-id]
```

### Weka

#### AWS

##### Create Template and Stack

This command creates a CloudFormation template dynamically and then uses that template
to launch a stack in AWS. You can alternatively use the create-template and create-stack 
sub commands to support advanced use cases.

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
--client-instance-type r3.xlarge \
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

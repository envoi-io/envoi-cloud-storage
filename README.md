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

[Weka Installation on AWS Using CloudFormation](https://docs.weka.io/planning-and-installation/aws/weka-installation-on-aws-using-the-cloud-formation)

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


```

export AWS_DEFAULT_REGION=us-east-1
export AWS_PROFILE=
export KEY_NAME=
export SUBNET_ID=
export VPC_ID=


Create Qumulo Cluster


Qumulo-1TB-FileStorageCluster-SSD-ONLY.template

./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo1TB \
--cluster-name qumulo1TB \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://s3.amazonaws.com/awsmp-fulfillment-cf-templates-prod/edeb9751-4819-40ad-a593-04b6572694e7.e37c83b0-7b23-4689-9c29-38d08cfd2952.template



Qumulo-12TB-FileStorageCluster-SSD+HDD.template
Use this template to quickly get up and running with a 12.7TB capacity cluster. Upon launch, this stack will create 4 EC2 instances from the parameterized instance type. Each instance will contain 5x100GiB EBS gp2 volumes for SSD cache and 10x500GiB EBS st1 volumes for HDD-backed data storage.
<https://aws.amazon.com/marketplace/pp/prodview-6ugmai2oluviy?sr=0-3&ref_=beagle&applicationId=AWSMPContessa>


./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo12TBb \
--cluster-name qumulo12TBb \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-12TB-FileStorageCluster-SSD%2BHDD.template \
--log-level debug



Qumulo-96TB-FileStorageCluster-SSD+HDD.template
Use this template to quickly get up and running with a 96.0TB capacity cluster. Upon launch, this stack will create 6 EC2 instances from the parameterized instance type. Each instance will contain 5x160GiB EBS gp2 volumes for SSD cache and 10x2000GiB EBS st1 volumes for HDD-backed data storage. 
<https://aws.amazon.com/marketplace/pp/prodview-6hfmu7wxbuvh2?sr=0-5&ref_=beagle&applicationId=AWSMPContessa>

./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-12TB-SSD+HDD \
--cluster-name qumulo-12TB-SSD+HDD \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-96TB-FileStorageCluster-SSD%2BHDD.template

Qumulo-103TB-Performance-FileStorageCluster-SSDOnly.template
Use this template to quickly get up and running with a 103.2TB capacity cluster. Upon launch, this stack will create 5 EC2 instances from the parameterized instance type. Each instance will contain 8x3750GiB EBS gp2 volumes for high-performance SSD data storage.
<https://aws.amazon.com/marketplace/pp/prodview-v75ikvi57xv66?sr=0-6&ref_=beagle&applicationId=AWSMPContessa>


./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-103TB-SSD-ONLY \
--cluster-name qumulo-103TB-SSD-ONLY \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-103TB-Performance-FileStorageCluster-SSDOnly.template



Qumulo-270TB-FileStorageCluster-SSD+HDD.template
Use this template to quickly get up and running with a 270.6TB capacity cluster. Upon launch, this stack will create 6 EC2 instances from the parameterized instance type. Each instance will contain 5x550GiB EBS gp2 volumes for SSD cache and 10x5632GiB EBS st1 volumes for HDD-backed data storage.
<https://aws.amazon.com/marketplace/pp/prodview-bf2p7jfejyb7k?sr=0-7&ref_=beagle&applicationId=AWSMPContessa>

./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-270TB-SSD+HDD \
--cluster-name qumulo-270TB-SSD+HDD \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-270TB-FileStorageCluster-SSD%2BHDD.template



Qumulo-809TB-FileStorageCluster-SSD+HDD.template
Use this template to quickly get up and running with a 809.0TB capacity cluster. Upon launch, this stack will create 6 EC2 instances from the parameterized instance type. Each instance will contain 8x1000GiB EBS gp2 volumes for SSD cache and 16x10240GiB EBS st1 volumes for HDD-backed data storage.
<https://aws.amazon.com/marketplace/pp/prodview-azxitkzmakbka?sr=0-4&ref_=beagle&applicationId=AWSMPContessa>


./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-809TB-SSD+HDD \
--cluster-name qumulo-809TB-SSD+HDD \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-809TB-FileStorageCluster-SSD%2BHDD.template


```

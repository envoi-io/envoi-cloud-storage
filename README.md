### Envoi Cloud Storage

Envoi Cloud Storage provides a suite of tools for provisioning and managing high-performance file systems on cloud platforms, with a focus on **WekaIO** and **Qumulo** on **Amazon Web Services (AWS)**. These solutions are designed to handle demanding workloads like video editing, VFX, and machine learning by providing high throughput and low latency.

-----

### Installation

#### Prerequisites

To use these utilities, you must have the **AWS CLI** installed and configured with appropriate credentials.

-----

### Usage

### Weka

#### AWS

##### Create Weka AWS CloudFormation Template and Launch CloudFormation Stack

This utility automates the creation of a Weka file system by leveraging the Weka API to generate an AWS CloudFormation template. This simplifies the deployment of a high-performance storage solution. You can choose to deploy a pre-configured 30TB file system with 7.6GB/s of throughput.

For advanced use cases, you can use the `create-template` and `create-stack` subcommands separately.

**Environment Variables**

To run the commands, you'll first need to set the following environment variables:

```shell
export AWS_DEFAULT_REGION='us-east-1'
export AWS_PROFILE='AWS_PROFILE'
export WEKA_API_TOKEN='WEKA_API_TOKEN'
export KEY_NAME='KEY_NAME'
export SUBNET_ID='SUBNET_ID'
export VPC_ID='VPC_ID'
```

**Required Arguments Example**

The following command demonstrates the minimum required arguments to create and launch a Weka stack. It provisions a 30TB file system with a backend of `i3en.6xlarge` instances.

```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID \
--backend-instance-type i3en.6xlarge \
--backend-instance-count 6 \
--client-instance-count 2 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--log-level debug
```

**Deploying a Weka 30TB File System with Specific Clients**

You can also specify the type and number of client instances to be launched along with the Weka file system. This is useful for pre-configuring your virtual desktops for specific creative applications.

**1. HP Anyware CentOS 7 Linux Clients**

This command launches the Weka file system and two client instances with HP Anyware on CentOS 7, using `g4dn.16xlarge` instances which are suitable for GPU-intensive workloads.

```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID \
--backend-instance-type i3en.6xlarge \
--backend-instance-count 10 \
--client-instance-type g4dn.16xlarge \
--client-instance-count 5 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--client-ami-id "ami-08447c4aa12458688 | us-east-1, ami-08190d20c372f54cc | us-west-1 ami-0805e10141cf4a781 | us-west-2"
```

**2. HP Anyware Windows Server 2019 (NVIDIA) Clients**

This command provisions a Weka file system with client instances running HP Anyware on Windows Server 2019 with NVIDIA GPUs.

```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID \
--backend-instance-type i3en.6xlarge \
--backend-instance-count 10 \
--client-instance-type g5.12xlarge \
--client-instance-count 5 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--client-ami-id "ami-08447c4aa12458688 | us-east-1, ami-08190d20c372f54cc | us-west-1 ami-0805e10141cf4a781 | us-west-2"
```

**3. HP Anyware Unreal Engine 5 on Windows 2022 Server Clients**

This command deploys the Weka file system and clients optimized for running Unreal Engine 5 on Windows Server 2022.

```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID \
--backend-instance-type i3en.6xlarge \
--backend-instance-count 10 \
--client-instance-type g5.12xlarge \
--client-instance-count 5 \
--stack-name envoi-storage-fs-4 \
--aws-profile $AWS_PROFILE \
--aws-region $AWS_DEFAULT_REGION \
--client-ami-id "ami-08447c4aa12458688 | us-east-1, ami-08190d20c372f54cc | us-west-1 ami-0805e10141cf4a781 | us-west-2"
```

-----

### Qumulo

#### AWS

##### Create Cluster

This utility creates a **Cloud Native Qumulo (CNQ)** cluster on AWS using a CloudFormation template. It provides a straightforward way to deploy a scalable, high-performance file storage solution.

**Command-Line Arguments**

  * `--log-level LOG_LEVEL`: Sets the logging level.
  * `--template-url TEMPLATE_URL`: **(Required)** The URL of the CloudFormation template for the specific cluster configuration.
  * `--cluster-name CLUSTER_NAME`: **(Required)** The name for the Qumulo cluster.
  * `--key-pair-name KEY_PAIR_NAME`: **(Required)** The SSH key pair name for instance access.
  * `--vpc-id VPC_ID`: **(Required)** The ID of the VPC where the cluster will be deployed.
  * `--subnet-id SUBNET_ID`: **(Required)** The ID of the subnet for the cluster nodes.
  * `--iam-instance-profile-name IAM_INSTANCE_PROFILE_NAME`: An optional IAM profile name.
  * `--instance-type INSTANCE_TYPE`: An optional instance type to override the template's default.
  * `--security-group-cidr SECURITY_GROUP_CIDR`: A CIDR block for security group access.
  * `--volumes-encryption-key VOLUMES_ENCRYPTION_KEY`: An optional KMS key for volume encryption.

**Setting Environment Variables**

```shell
export AWS_DEFAULT_REGION=us-east-1
export AWS_PROFILE=
export KEY_NAME=
export SUBNET_ID=
export VPC_ID=
```

**Creating a Qumulo Cluster**

Here are examples for deploying different Qumulo cluster sizes, each corresponding to a specific CloudFormation template URL.

**1. 1TB File Storage Cluster (SSD Only)**

This template creates a 1TB capacity cluster using only SSD volumes for high performance.

```bash
./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo1TB \
--cluster-name qumulo1TB \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://s3.amazonaws.com/awsmp-fulfillment-cf-templates-prod/edeb9751-4819-40ad-a593-04b6572694e7.e37c83b0-7b23-4689-9c29-38d08cfd2952.template
```

**2. 12TB File Storage Cluster (SSD + HDD)**

This template creates a 12.7TB capacity cluster using a hybrid of SSDs for cache and HDDs for data storage.

```bash
./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo12TBb \
--cluster-name qumulo12TBb \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-12TB-FileStorageCluster-SSD%2BHDD.template \
--log-level debug
```

**3. 96TB File Storage Cluster (SSD + HDD)**

This template creates a 96.0TB capacity cluster with a hybrid of SSD and HDD volumes.

```bash
./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-12TB-SSD+HDD \
--cluster-name qumulo-12TB-SSD+HDD \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-96TB-FileStorageCluster-SSD%2BHDD.template
```

**4. 103TB Performance File Storage Cluster (SSD Only)**

This template is for a high-performance 103.2TB cluster that uses only SSD volumes for maximum speed.

```bash
./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-103TB-SSD-ONLY \
--cluster-name qumulo-103TB-SSD-ONLY \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-103TB-Performance-FileStorageCluster-SSDOnly.template
```

**5. 270TB File Storage Cluster (SSD + HDD)**

This template provisions a large 270.6TB capacity cluster using a hybrid storage model.

```bash
./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-270TB-SSD+HDD \
--cluster-name qumulo-270TB-SSD+HDD \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-270TB-FileStorageCluster-SSD%2BHDD.template
```

**6. 809TB File Storage Cluster (SSD + HDD)**

This template creates a massive 809.0TB cluster for petabyte-scale workloads, combining SSDs and HDDs.

```bash
./envoi_storage.py qumulo aws create-cluster \
--stack-name qumulo-809TB-SSD+HDD \
--cluster-name qumulo-809TB-SSD+HDD \
--key-pair-name $KEY_NAME \
--vpc-id $VPC_ID \
--subnet-id $SUBNET_ID \
--template-url https://envoi-prod-files-public.s3.amazonaws.com/qumulo/cloud-formation/templates/Qumulo-809TB-FileStorageCluster-SSD%2BHDD.template
```

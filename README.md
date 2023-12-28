# Envoi Storage

## Installation

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

##### Create Template

Example using only required arguments
```shell
envoi-storage weka aws create-template \
--token {WEKA_API_TOKEN}
```

Example with backend and client instance arguments
```shell
envoi-storage weka aws create-template \
--token {WEKA_API_TOKEN} \
--backend-instance-type i3en.2xlarge \
--backend-instance-count 10 \
--client-instance-type r3.xlarge \
--client-instance-count 2
```

##### Create Template and Stack

Example using only required arguments
```shell
./envoi_storage.py weka aws create-template-and-stack \
--token WEKA_API_TOKEN \
--template-param-key-name KEY_NAME \
--template-param-subnet-id SUBNET_ID \
--template-param-vpc-id VPC_ID
```

### Hammerspace

#### AWS

```shell
envoi-storage hammerspace aws --hammerspce-deployment-type add | new --hammerspce-anvil-configuration standalone | cluster --hammerspce-anvil-ip-address 0.0.0.0 --hammerspce-anvil-instance-type m5.2xlarge --hammerspce-anvil-instance-disk-size 2000 --hammerspce-dsxnode-instance-type c5.24xlarge --hammerspce-dsxnode-instance-count 8 --hammerspce-dsxnode-instance-disk-size 16384 --hammerspce-dsxnode-instance-add-volumes yes --hammerspce-cluster-vpcd-id hammerspce-dev-vpc-id --hammerspce-cluster-availability-zone us-west-2a --hammerspce-cluster-security-group-cidr 0.0.0.0/0 --hammerspce-cluster-iam-instance-profile hammerspce-iam-instance-role-name --hammerspce-cluster-key-pair-name hammerspce-dev --hammerspce-cluster-enable-iam-user-access yes | no --hammerspce-cluster-enable-iam-user-group-id [iam--admin-group-id]
```


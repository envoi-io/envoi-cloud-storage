#!/bin/bash

# Define environment variables (default values)
export AWS_PROFILE="envoi-dev"
export AWS_DEFAULT_REGION="us-east-1"
export FSX_TYPE=""
export FSX_DEPLOYMENT_TYPE=""
export VPC_ID=""
export SUBNET_IDS=""
export AD_TYPE=""
export AD_ID=""
export AD_USERNAME=""
export AD_PASSWORD=""

# --- Functions for interactive menus ---

# Function to display the FSx type menu
function show_fsx_type_menu() {
  clear
  echo "Please select the Amazon FSx file system type:"
  echo "1) Amazon FSx for Windows File Server"
  echo "2) Amazon FSx for NetApp ONTAP"
  echo "Enter the number of your choice:"
}

# Function to display the Active Directory menu
function show_ad_menu() {
  clear
  echo "Please select the Active Directory option:"
  echo "1) Use an existing AWS Managed Microsoft AD"
  echo "2) Use an existing Self-Managed Active Directory"
  echo "3) Create a new AWS Managed Microsoft AD"
  echo "Enter the number of your choice:"
}

# Function to prompt for deployment type based on FSx type
function prompt_deployment_type() {
    clear
    local fsx_type_name=$1
    echo "Please select the deployment type for $fsx_type_name:"
    echo "1) SINGLE_AZ_1"
    echo "2) SINGLE_AZ_2"
    if [[ "$FSX_TYPE" == "WINDOWS" ]]; then
        echo "3) MULTI_AZ_1"
    elif [[ "$FSX_TYPE" == "ONTAP" ]]; then
        echo "3) MULTI_AZ_1"
        echo "4) MULTI_AZ_2"
    fi
    echo ""
    read -p "Enter the number of your choice: " DEPLOYMENT_CHOICE

    case "$DEPLOYMENT_CHOICE" in
        1) FSX_DEPLOYMENT_TYPE="SINGLE_AZ_1" ;;
        2) FSX_DEPLOYMENT_TYPE="SINGLE_AZ_2" ;;
        3) 
            if [[ "$FSX_TYPE" == "WINDOWS" ]] || [[ "$FSX_TYPE" == "ONTAP" ]]; then
                FSX_DEPLOYMENT_TYPE="MULTI_AZ_1"
            else
                echo "Invalid choice. Exiting."
                exit 1
            fi
            ;;
        4) 
            if [[ "$FSX_TYPE" == "ONTAP" ]]; then
                FSX_DEPLOYMENT_TYPE="MULTI_AZ_2"
            else
                echo "Invalid choice. Exiting."
                exit 1
            fi
            ;;
        *)
            echo "Invalid choice. Exiting."
            exit 1
            ;;
    esac
}

# --- Main script logic ---

# Step 1: Prompt for FSx File System Type selection
show_fsx_type_menu
read -p "Your choice: " FSX_TYPE_CHOICE

case "$FSX_TYPE_CHOICE" in
    1) FSX_TYPE="WINDOWS" ;;
    2) FSX_TYPE="ONTAP" ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Step 2: Determine supported regions for the selected FSx service
clear
echo "Fetching regions that support FSx for $FSX_TYPE..."
echo ""
REGION_LIST_TEXT=$(aws ssm get-parameters-by-path --path /aws/service/global-infrastructure/services/fsx/regions --output json | grep -o '\"Value\": \"[a-z0-9-]*\"' | cut -d'"' -f4)
if [ -z "$REGION_LIST_TEXT" ]; then
    echo "Failed to retrieve AWS regions. Check your AWS CLI configuration and permissions. Exiting."
    exit 1
fi

echo "Please select the AWS Region:"
i=0
REGION_CHOICES=()
while read -r region; do
    REGION_CHOICES[$i]="$region"
    echo "$((i+1))) $region"
    i=$((i+1))
done <<< "$REGION_LIST_TEXT"

echo "Enter the number of your choice:"
read -p "Your choice: " REGION_CHOICE
SELECTED_REGION="${REGION_CHOICES[$((REGION_CHOICE-1))]}"
export AWS_DEFAULT_REGION="$SELECTED_REGION"

echo ""
echo "You have selected Region: $SELECTED_REGION"

# Step 3: Prompt for Deployment Type
if [[ "$FSX_TYPE" == "WINDOWS" ]]; then
    prompt_deployment_type "Windows File Server"
elif [[ "$FSX_TYPE" == "ONTAP" ]]; then
    prompt_deployment_type "NetApp ONTAP"
fi

echo "You have selected deployment type: $FSX_DEPLOYMENT_TYPE"

# Step 4: Active Directory Configuration
show_ad_menu
read -p "Your choice: " AD_CHOICE

case "$AD_CHOICE" in
    1)
        # Use existing AWS Managed AD
        echo ""
        echo "Please select the region where your AWS Managed Microsoft AD is located:"
        i=0
        while read -r region; do
            echo "$((i+1))) $region"
            i=$((i+1))
        done <<< "$REGION_LIST_TEXT"
        echo ""
        read -p "Enter the number of your choice (or enter 'q' to query all services): " AD_REGION_CHOICE

        if [[ "$AD_REGION_CHOICE" == "q" ]]; then
            echo ""
            echo "Querying all AWS Managed ADs across all regions..."
            # This part can be slow, but it's the most comprehensive way to find the AD
            ALL_AD_IDS=$(aws ds describe-directories --query "DirectoryDescriptions[*].[DirectoryId, Name, Region]" --output text)
            if [ -z "$ALL_AD_IDS" ]; then
                echo "No AWS Managed ADs found in any region. Exiting."
                exit 1
            fi
            echo "Found AWS Managed ADs:"
            echo "$ALL_AD_IDS" | nl
            read -p "Please select an AD by number: " AD_ID_CHOICE
            AD_ID=$(echo "$ALL_AD_IDS" | sed -n "${AD_ID_CHOICE}p" | awk '{print $1}')
            AD_TYPE="MANAGED"
        else
            AD_REGION="${REGION_CHOICES[$((AD_REGION_CHOICE-1))]}"
            echo ""
            echo "Fetching existing AWS Managed Active Directories in region $AD_REGION..."
            AD_IDS=$(aws ds describe-directories --query "DirectoryDescriptions[*].[DirectoryId, Name]" --output text --region "$AD_REGION")
            if [ -z "$AD_IDS" ]; then
                echo "No AWS Managed ADs found in region $AD_REGION. Exiting."
                exit 1
            fi
            echo "Available AWS Managed ADs:"
            echo "$AD_IDS" | nl
            read -p "Please select an AD by number: " AD_ID_CHOICE
            AD_ID=$(echo "$AD_IDS" | sed -n "${AD_ID_CHOICE}p" | awk '{print $1}')
            AD_TYPE="MANAGED"
        fi

        if [ -z "$AD_ID" ]; then
            echo "Invalid AD selection. Exiting."
            exit 1
        fi
        ;;
    2)
        # Use existing Self-Managed AD
        echo ""
        echo "Please provide details for your Self-Managed Active Directory:"
        read -p "Domain Name (e.g., ad.example.com): " DOMAIN_NAME
        read -p "DNS IP Address (e.g., 10.0.1.1,10.0.2.2): " DNS_IPS
        read -p "Admin Username: " AD_USERNAME
        read -p "Admin Password: " AD_PASSWORD
        read -p "VPC ID where AD is located: " SELF_MANAGED_VPC_ID
        read -p "Subnet IDs for AD DNS: " SELF_MANAGED_SUBNET_IDS
        AD_TYPE="SELF_MANAGED"
        ;;
    3)
        # Create a new AWS Managed AD
        echo ""
        echo "Initiating new AWS Managed AD creation..."
        
        # We can't just create it here, it takes too long.
        # We'll just capture the info and tell the user they need to create it.
        echo "This script does not create the AD directory itself due to the time it takes."
        echo "You will need to create it manually and then re-run this script to select it."
        echo "Exiting now. Please run the directory creation script from the previous conversation."
        exit 1
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Step 5: Select VPC and Subnets
# For self-managed, we use the user-provided VPC/Subnets. For managed, we use the FSx VPC/Subnets.
if [[ "$AD_TYPE" == "SELF_MANAGED" ]]; then
    VPC_ID="$SELF_MANAGED_VPC_ID"
    SUBNET_IDS="$SELF_MANAGED_SUBNET_IDS"
else
    echo ""
    echo "Fetching available VPCs..."
    VPC_IDS=$(aws ec2 describe-vpcs --region "$SELECTED_REGION" --query "Vpcs[*].[VpcId, Tags[?Key=='Name'].Value|[0]]" --output text)
    if [ -z "$VPC_IDS" ]; then
      echo "No VPCs found. Exiting."
      exit 1
    fi
    echo "Available VPCs:"
    echo "$VPC_IDS" | nl
    read -p "Please select a VPC ID by number: " VPC_CHOICE
    VPC_ID=$(echo "$VPC_IDS" | sed -n "${VPC_CHOICE}p" | awk '{print $1}')
    if [ -z "$VPC_ID" ]; then
      echo "Invalid VPC selection. Exiting."
      exit 1
    fi
    
    echo ""
    echo "Fetching available Subnets in VPC $VPC_ID..."
    SUBNETS=$(aws ec2 describe-subnets --region "$SELECTED_REGION" --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].[SubnetId,AvailabilityZone]" --output text)
    if [ -z "$SUBNETS" ]; then
      echo "No subnets found for the selected VPC. Exiting."
      exit 1
    fi
    echo "Available Subnets:"
    SUBNET_INFO=()
    while read -r SUBNET_ID AZ; do
      SUBNET_INFO+=("$SUBNET_ID $AZ")
    done <<< "$SUBNETS"
    for i in "${!SUBNET_INFO[@]}"; do
      printf "%d) %s\n" $((i+1)) "${SUBNET_INFO[$i]}"
    done
    echo ""

    # Determine the number of subnets to select based on deployment type
    case "$FSX_DEPLOYMENT_TYPE" in
        SINGLE_AZ_1|SINGLE_AZ_2)
            read -p "Please enter the number of the subnet you would like to use: " SUBNET_CHOICES
            SUBNET_IDS=$(echo "${SUBNET_INFO[$((SUBNET_CHOICES-1))]}" | awk '{print $1}')
            if [ -z "$SUBNET_IDS" ]; then
                echo "Invalid Subnet selection. Exiting."
                exit 1
            fi
            ;;
        MULTI_AZ_1|MULTI_AZ_2)
            read -p "Please enter the numbers of the two subnets you would like to use, separated by a comma (e.g., 1,2): " SUBNET_CHOICES
            IFS=',' read -r -a SUBNET_ARRAY <<< "$SUBNET_CHOICES"
            if [ ${#SUBNET_ARRAY[@]} -ne 2 ]; then
                echo "You must select exactly two subnets for a multi-AZ deployment. Exiting."
                exit 1
            fi
            SUBNET_1_ID=$(echo "${SUBNET_INFO[$((SUBNET_ARRAY[0]-1))]}" | awk '{print $1}')
            SUBNET_2_ID=$(echo "${SUBNET_INFO[$((SUBNET_ARRAY[1]-1))]}" | awk '{print $1}')
            SUBNET_IDS="$SUBNET_1_ID,$SUBNET_2_ID"
            if [ -z "$SUBNET_IDS" ]; then
                echo "Invalid Subnet selections. Exiting."
                exit 1
            fi
            ;;
    esac
fi

# Step 6: Confirmation and Execution
echo ""
echo "You have chosen to deploy an Amazon FSx file system with the following settings:"
echo "File System Type: $FSX_TYPE"
echo "Region: $SELECTED_REGION"
echo "Deployment Type: $FSX_DEPLOYMENT_TYPE"
echo "VPC ID: $VPC_ID"
echo "Subnet IDs: $SUBNET_IDS"
if [[ "$AD_TYPE" == "MANAGED" ]]; then
    echo "Active Directory: Existing AWS Managed AD ($AD_ID)"
elif [[ "$AD_TYPE" == "SELF_MANAGED" ]]; then
    echo "Active Directory: Self-Managed ($DOMAIN_NAME)"
    echo "DNS IPs: $DNS_IPS"
    echo "Admin Username: $AD_USERNAME"
fi
echo ""

# Construct the create-file-system command
if [[ "$FSX_TYPE" == "WINDOWS" ]]; then
    if [[ "$AD_TYPE" == "MANAGED" ]]; then
        CREATE_COMMAND="aws fsx create-file-system --region \"$SELECTED_REGION\" --file-system-type WINDOWS --subnet-ids \"$SUBNET_IDS\" --windows-configuration \"ActiveDirectoryId=$AD_ID,DeploymentType=$FSX_DEPLOYMENT_TYPE,ThroughputCapacity=32\" --profile \"$AWS_PROFILE\""
    elif [[ "$AD_TYPE" == "SELF_MANAGED" ]]; then
        CREATE_COMMAND="aws fsx create-file-system --region \"$SELECTED_REGION\" --file-system-type WINDOWS --subnet-ids \"$SUBNET_IDS\" --windows-configuration \"SelfManagedActiveDirectoryConfiguration={DomainName=$DOMAIN_NAME,DnsIps=[$DNS_IPS],UserName=$AD_USERNAME,Password=$AD_PASSWORD}\",DeploymentType=\"$FSX_DEPLOYMENT_TYPE\",ThroughputCapacity=32\" --profile \"$AWS_PROFILE\""
    fi
elif [[ "$FSX_TYPE" == "ONTAP" ]]; then
    if [[ "$AD_TYPE" == "MANAGED" ]]; then
        CREATE_COMMAND="aws fsx create-file-system --region \"$SELECTED_REGION\" --file-system-type ONTAP --subnet-ids \"$SUBNET_IDS\" --ontap-configuration \"PreferredSubnetId=$SUBNET_IDS,DeploymentType=\"$FSX_DEPLOYMENT_TYPE\"\" --profile \"$AWS_PROFILE\""
    elif [[ "$AD_TYPE" == "SELF_MANAGED" ]]; then
        CREATE_COMMAND="aws fsx create-file-system --region \"$SELECTED_REGION\" --file-system-type ONTAP --subnet-ids \"$SUBNET_IDS\" --ontap-configuration \"PreferredSubnetId=$SUBNET_IDS,DeploymentType=\"$FSX_DEPLOYMENT_TYPE\"\" --profile \"$AWS_PROFILE\""
    fi
fi

echo "The following command will be executed upon confirmation:"
echo ""
echo "$CREATE_COMMAND"
echo ""

read -p "Would you like to proceed with the deployment? (y/n): " CONFIRM_DEPLOY
if [[ ! "$CONFIRM_DEPLOY" =~ ^[yY]$ ]]; then
  echo "Deployment canceled by user. Exiting."
  exit 0
fi

# Step 7: Execute the command
echo ""
echo "Creating Amazon FSx file system..."
# The actual execution using eval to handle complex arguments
eval $CREATE_COMMAND

echo ""
echo "Script completed. Your Amazon FSx file system is being created."
echo "Note: This process can take a while to complete. You can monitor its status in the AWS FSx console."
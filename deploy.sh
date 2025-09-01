#!/bin/bash

# Doctor Appointment Monitor - Azure Deployment Script
# This script helps deploy the function app to Azure

set -e  # Exit on any error

echo "🏥 Doctor Appointment Monitor - Azure Deployment"
echo "================================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install Azure CLI first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if Functions Core Tools are installed
if ! command -v func &> /dev/null; then
    echo "❌ Azure Functions Core Tools not found. Please install:"
    echo "   npm install -g azure-functions-core-tools@4 --unsafe-perm true"
    exit 1
fi

# Get deployment configuration
read -p "Enter your Azure subscription ID: " SUBSCRIPTION_ID
read -p "Enter your resource group name (will be created if doesn't exist): " RESOURCE_GROUP
read -p "Enter your storage account name (will be created if doesn't exist): " STORAGE_ACCOUNT
read -p "Enter your function app name: " FUNCTION_APP_NAME
read -p "Enter Azure region [eastus]: " LOCATION
LOCATION=${LOCATION:-eastus}

# Get Pushover configuration
echo ""
echo "📱 Pushover Configuration"
echo "----------------------"
read -p "Enter your Pushover app token: " PUSHOVER_TOKEN
read -p "Enter your Pushover user key: " PUSHOVER_USER

# Optional: Azure Storage connection for duplicate prevention
echo ""
read -p "Use Azure Storage for duplicate notification prevention? (y/N): " USE_STORAGE
AZURE_STORAGE_CONNECTION_STRING=""

echo ""
echo "🚀 Starting deployment..."

# Set subscription
echo "Setting Azure subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

# Create resource group if it doesn't exist
echo "Creating resource group if needed..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# Create storage account if it doesn't exist
echo "Creating storage account if needed..."
az storage account create \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --output none

if [ "$USE_STORAGE" = "y" ] || [ "$USE_STORAGE" = "Y" ]; then
    # Get storage connection string
    echo "Getting storage connection string..."
    AZURE_STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --query connectionString \
        --output tsv)
fi

# Create function app
echo "Creating Azure Function App..."
az functionapp create \
    --resource-group "$RESOURCE_GROUP" \
    --consumption-plan-location "$LOCATION" \
    --runtime python \
    --runtime-version 3.11 \
    --functions-version 4 \
    --name "$FUNCTION_APP_NAME" \
    --storage-account "$STORAGE_ACCOUNT" \
    --output none

# Set application settings
echo "Configuring application settings..."
az functionapp config appsettings set \
    --name "$FUNCTION_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --settings \
    "TARGET_URL=https://booking.opto.com/5d71635fb4fd7/marpole-optometry-clinic/schedules/87545935-0F15-4210-8F45-CDDC6C7F2395/" \
    "DOCTOR_NAME=Cornnie" \
    "PUSHOVER_TOKEN=$PUSHOVER_TOKEN" \
    "PUSHOVER_USER=$PUSHOVER_USER" \
    "AZURE_STORAGE_CONNECTION_STRING=$AZURE_STORAGE_CONNECTION_STRING" \
    --output none

# Deploy the function
echo "Deploying function code..."
cd doctor-watch
func azure functionapp publish "$FUNCTION_APP_NAME" --python

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Function App Details:"
echo "   Name: $FUNCTION_APP_NAME"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
echo ""
echo "🔍 Monitor your function:"
echo "   Azure Portal: https://portal.azure.com"
echo "   Logs: az functionapp logs tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "⏰ The function will start monitoring appointments every 5 minutes automatically."
echo "📱 You'll receive notifications on your iOS device via Pushover when appointments are found."

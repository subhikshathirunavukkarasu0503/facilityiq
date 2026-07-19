# FacilityIQ — Azure provisioning (free tiers only, per RFP budget)
# Prereq: az login already completed.
# Creates: resource group, IoT Hub (F1), Storage (Standard_LRS), device identity.
# App Service deploy handled separately (scripts/azure_deploy_portal.ps1).

$ErrorActionPreference = "Stop"

$RG      = "facilityiq-rg"
$LOC     = "centralindia"
$HUB     = "facilityiq-hub"
$STORAGE = "facilityiqlake$(Get-Random -Maximum 9999)"
$DEVICE  = "facilityiq-simulator"

Write-Host "== Resource group =="
az group create --name $RG --location $LOC --output table

Write-Host "== IoT Hub (F1 free tier: 8,000 msgs/day) =="
az iot hub create --name $HUB --resource-group $RG --sku F1 --partition-count 2 --output table

Write-Host "== Storage account (data lake) =="
az storage account create --name $STORAGE --resource-group $RG `
    --location $LOC --sku Standard_LRS --kind StorageV2 --output table
az storage container create --name telemetry --account-name $STORAGE --auth-mode login --output table

Write-Host "== Device identity =="
az iot hub device-identity create --hub-name $HUB --device-id $DEVICE --output table

Write-Host "== Connection string (put in .env as IOTHUB_DEVICE_CONNECTION_STRING) =="
az iot hub device-identity connection-string show --hub-name $HUB --device-id $DEVICE --output tsv

Write-Host "== Route telemetry to storage =="
$storageConn = az storage account show-connection-string --name $STORAGE --resource-group $RG --output tsv
az iot hub routing-endpoint create --hub-name $HUB --resource-group $RG `
    --endpoint-name lake --endpoint-type azurestoragecontainer `
    --endpoint-resource-group $RG --endpoint-subscription-id (az account show --query id -o tsv) `
    --connection-string $storageConn --container telemetry `
    --encoding json --batch-frequency 60 --chunk-size 10
az iot hub route create --hub-name $HUB --resource-group $RG `
    --route-name all-to-lake --source devicemessages --endpoint-name lake --enabled true

Write-Host "DONE. Budget impact: 0 (all free tier)."

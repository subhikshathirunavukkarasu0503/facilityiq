# FacilityIQ — full Azure teardown. Run after the demo to zero out all cost.
# Deletes the entire resource group (IoT Hub, storage, everything inside).
az group delete --name facilityiq-rg --yes --no-wait
Write-Host "Deletion started. Verify later with: az group exists --name facilityiq-rg"

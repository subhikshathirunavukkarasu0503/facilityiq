# FacilityIQ — Azure teardown. Run after final demo to zero out cost.
# IMPORTANT: deletes ONLY resources we created inside the company-assigned
# resource group. Never delete the resource group itself — it belongs to
# Psiog IT (rg-pSiddhi3.0-2026-01-sem4-Subhiksha).

$RG = "rg-pSiddhi3.0-2026-01-sem4-Subhiksha"

az storage account delete --name fiqlake28091 --resource-group $RG --yes
Write-Host "Storage account fiqlake28091 deleted. Remaining cost: 0."
Write-Host "If IT later created an IoT Hub / App Service for you, ask them to remove those too."

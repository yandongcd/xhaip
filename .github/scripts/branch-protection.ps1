# xhaip Branch Protection Rules -- Apply to 'main' branch
#
# Prerequisites:
#   1. gh auth login (with admin:repo scope)
#   2. Run from repo root
#
# Usage: powershell -ExecutionPolicy Bypass -File .github\scripts\branch-protection.ps1

$REPO = "yandongcd/xhaip"
$BRANCH = "main"

$payload = @{
    required_status_checks = $null
    enforce_admins = $true
    required_pull_request_reviews = @{
        dismissal_restrictions = @{}
        dismiss_stale_reviews = $true
        require_code_owner_reviews = $true
        required_approving_review_count = 1
        require_last_push_approval = $false
        bypass_pull_request_allowances = @{
            users = @("tianlinyi")
            teams = @()
        }
    }
    restrictions = $null
    required_linear_history = $false
    allow_force_pushes = $false
    allow_deletions = $false
    block_creations = $false
    required_conversation_resolution = $false
    lock_branch = $false
    allow_fork_syncing = $true
} | ConvertTo-Json -Depth 10

Write-Host "Applying branch protection to $REPO / $BRANCH ..."
Write-Host ""
Write-Host $payload
Write-Host ""

gh api repos/$REPO/branches/$BRANCH/protection --method PUT --input - <<< $payload

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] Branch protection applied successfully."
    Write-Host ""
    Write-Host "Settings applied:"
    Write-Host "  - Require PR before merging: YES"
    Write-Host "  - Require approvals: 1"
    Write-Host "  - Dismiss stale reviews: YES"
    Write-Host "  - Require CODEOWNERS review: YES"
    Write-Host "  - Include administrators: YES"
    Write-Host "  - Force push: BLOCKED"
    Write-Host "  - Branch deletion: BLOCKED"
} else {
    Write-Host ""
    Write-Host "[ERROR] Failed to apply branch protection. Check token permissions."
    Write-Host "  Required scope: admin:repo"
}
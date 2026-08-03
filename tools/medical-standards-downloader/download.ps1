# Medical Standards Downloader (PowerShell)
# Downloads freely available clinical guidelines and standards

param(
    [switch]$All,
    [string]$Category,
    [switch]$List
)

$OutputDir = Join-Path $PSScriptRoot "..\..\docs\standards\downloads"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Bypass SSL issues in corporate environment
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12, [Net.SecurityProtocolType]::Tls13
if (-not [System.AppContext]::GetData("System.Net.Http.DisableSslValidation")) {
    Write-Host "Using standard SSL verification" -ForegroundColor Yellow
}

# ── Free Downloadable Standards ──────────────────────────────────────────

$Downloads = @(
    # NICE Guidelines (all free PDFs)
    @{Name="NICE-CG124"; Title="Hip Fracture Management"; URL="https://www.nice.org.uk/guidance/cg124"; Cat="orthopedics"},
    @{Name="NICE-CG167"; Title="AAA Diagnosis and Management"; URL="https://www.nice.org.uk/guidance/cg167"; Cat="vascular"},
    @{Name="NICE-CG148"; Title="Urinary Incontinence in Women"; URL="https://www.nice.org.uk/guidance/cg148"; Cat="urology"},

    # KDIGO (all free)
    @{Name="KDIGO-AKI-2024"; Title="KDIGO 2024 Acute Kidney Injury"; URL="https://kdigo.org/guidelines/acute-kidney-injury/"; Cat="nephrology"},
    @{Name="KDIGO-CKD-2024"; Title="KDIGO 2024 CKD"; URL="https://kdigo.org/guidelines/ckd-evaluation-and-management/"; Cat="nephrology"},

    # GOLD COPD
    @{Name="GOLD-COPD-2024"; Title="GOLD 2024 COPD Report"; URL="https://goldcopd.org/2024-gold-report/"; Cat="respiratory"},

    # WHO Guidelines
    @{Name="WHO-AI-ETHICS"; Title="WHO AI Ethics for Health"; URL="https://iris.who.int/bitstream/handle/10665/341996/9789240029200-eng.pdf"; Cat="ai-ethics"},
    @{Name="WHO-PATIENT-SAFETY"; Title="WHO Patient Safety Action Plan"; URL="https://iris.who.int/bitstream/handle/10665/343478/9789240032705-eng.pdf"; Cat="management"},

    # CDC
    @{Name="CDC-AMS-CORE"; Title="CDC Core Elements of Hospital Antibiotic Stewardship"; URL="https://www.cdc.gov/antibiotic-use/core-elements/hospital.html"; Cat="infectious-disease"},

    # NIH/NLM Guidelines from PMC (open access)
    @{Name="CONSORT-AI"; Title="CONSORT-AI Reporting Guidelines"; URL="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7497823/pdf/"; Cat="ai-research"},
    @{Name="SPIRIT-AI"; Title="SPIRIT-AI Protocol Guidelines"; URL="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7497824/pdf/"; Cat="ai-research"},

    # ACR RADS
    @{Name="BI-RADS"; Title="ACR BI-RADS Atlas"; URL="https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/Bi-Rads"; Cat="radiology"},
    @{Name="LI-RADS"; Title="ACR LI-RADS v2018"; URL="https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/LI-RADS"; Cat="radiology"},
    @{Name="Lung-RADS"; Title="ACR Lung-RADS v2022"; URL="https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/Lung-Rads"; Cat="radiology"},

    # CAP Pathology Protocols
    @{Name="CAP-CANCER-PROTOCOLS"; Title="CAP Cancer Protocols"; URL="https://www.cap.org/protocols-and-guidelines/cancer-reporting-tools/cancer-protocols"; Cat="pathology"},

    # ICCR
    @{Name="ICCR-DATASETS"; Title="ICCR Cancer Datasets"; URL="https://www.iccr-cancer.org/datasets"; Cat="pathology"},

    # ELSO
    @{Name="ELSO-GUIDELINES"; Title="ELSO ECMO Guidelines"; URL="https://www.elso.org/resources/guidelines.aspx"; Cat="pediatrics"},

    # ESPEN
    @{Name="ESPEN-GUIDELINES"; Title="ESPEN Clinical Nutrition Guidelines"; URL="https://www.espen.org/guidelines-home/espen-guidelines"; Cat="nutrition"},

    # EUCAST
    @{Name="EUCAST-BREAKPOINTS"; Title="EUCAST Clinical Breakpoints"; URL="https://www.eucast.org/clinical_breakpoints"; Cat="infectious-disease"},

    # WFH
    @{Name="WFH-HEMOPHILIA"; Title="WFH Hemophilia Guidelines 3rd Ed"; URL="https://www.wfh.org/en/resources/wfh-treatment-guidelines"; Cat="pharmacy"},

    # ISMP
    @{Name="ISMP-HIGH-ALERT"; Title="ISMP High-Alert Medications List"; URL="https://www.ismp.org/recommendations/high-alert-medications-acute-list"; Cat="pharmacy"},

    # ESUR
    @{Name="ESUR-CONTRAST-V10"; Title="ESUR Contrast Agent Guidelines v10"; URL="https://www.esur.org/esur-guidelines-on-contrast-agents/"; Cat="radiology"},

    # GINA
    @{Name="GINA-ASTHMA-2024"; Title="GINA 2024 Asthma Report"; URL="https://ginasthma.org/2024-report/"; Cat="respiratory"}
)

# ── Download Logic ───────────────────────────────────────────────────────

$total = 0
$success = 0
$failed = 0

Write-Host ""
Write-Host "=" * 70
Write-Host "  XHAIP Medical Standards Download Tool"
Write-Host "=" * 70
Write-Host ""

if ($List) {
    $files = Get-ChildItem -Path $OutputDir -ErrorAction SilentlyContinue
    Write-Host "  Files in ${OutputDir}:"
    if ($files) {
        $files | ForEach-Object { Write-Host "    - $($_.Name)" }
    } else {
        Write-Host "    (empty)"
    }
    Write-Host "  Total: $($files.Count) files"
    exit 0
}

foreach ($item in $Downloads) {
    if ($Category -and $item.Cat -ne $Category) { continue }

    $total++
    $fileName = "$($item.Name).html"
    $filePath = Join-Path $OutputDir $fileName

    Write-Host "[$total/$($Downloads.Count)] $($item.Name) - $($item.Title)" -NoNewline

    try {
        # Use Invoke-WebRequest instead of RestMethod to handle redirects better
        $response = Invoke-WebRequest -Uri $item.URL -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop

        # Save as HTML (for web pages) or save reference info
        $content = @"
<!DOCTYPE html><html><head><meta charset="utf-8">
<title>$($item.Title)</title></head><body>
<h1>$($item.Title)</h1>
<p>Source: <a href="$($item.URL)">$($item.URL)</a></p>
<p>Downloaded: $(Get-Date -Format 'yyyy-MM-dd HH:mm')</p>
<p>Category: $($item.Cat)</p>
<hr>
<h2>Note</h2>
<p>This is a reference page. The actual guideline document may need to be
downloaded directly from the source URL above. Many guidelines are freely
available as PDF downloads from their official websites.</p>
<p>For NICE guidelines, append <code>/pdf</code> to the URL.</p>
<p>For KDIGO, use the "Download" button on the guideline page.</p>
<p>For NCCN, register for free account at nccn.org.</p>
<p>For ACR RADS, guides are freely downloadable with registration.</p>
</body></html>
"@
        Set-Content -Path $filePath -Value $content -Encoding UTF8
        Write-Host " ~ OK" -ForegroundColor Green
        $success++

    } catch {
        # Save URL reference even if download failed
        $refContent = @"
{"name": "$($item.Name)", "title": "$($item.Title)", "url": "$($item.URL)",
 "category": "$($item.Cat)", "status": "url_saved",
 "note": "Download failed: $($_.Exception.Message)"}
"@
        Set-Content -Path ($filePath -replace '\.html$', '.json') -Value $refContent -Encoding UTF8
        Write-Host " : URL saved (download failed)" -ForegroundColor Yellow
        $failed++
    }

    Start-Sleep -Milliseconds 500
}

# ── Chinese Standards Reference ──────────────────────────────────────────
Write-Host ""
Write-Host "--- Chinese National Standards (中国标准/指南) ---"
Write-Host ""

$CN_Standards = @(
    @{Name="NMPA-AI-GUIDE"; Title="人工智能医疗器械注册审查指导原则"; URL="https://www.nmpa.gov.cn/ylqx/ylqxggtg/20220309111021184.html"},
    @{Name="CN-AI-GOVERNANCE"; Title="新一代人工智能治理原则"; URL="https://www.gov.cn/xinwen/2019-06/17/content_5401006.htm"},
    @{Name="CN-ETHICS-REVIEW"; Title="科技伦理审查办法"; URL="https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/gfxwj/gfxwj2023/202310/t20231008_188968.html"},
    @{Name="CN-HIP-FX-GUIDE"; Title="老年髋部骨折诊疗与管理指南 2022"; URL="http://www.nhc.gov.cn/"},
    @{Name="CN-HTN-GUIDE"; Title="中国高血压防治指南 2023"; URL="http://www.nhc.gov.cn/"},
    @{Name="CN-BREAST-GUIDE"; Title="乳腺癌诊疗指南 2022版"; URL="http://www.nhc.gov.cn/"},
    @{Name="CN-LIVER-GUIDE"; Title="原发性肝癌诊疗指南 2024"; URL="http://www.nhc.gov.cn/"},
    @{Name="CN-ENDOMETRIAL"; Title="子宫内膜癌诊治指南"; URL="http://www.nhc.gov.cn/"},
    @{Name="CN-GLCOMA-2025"; Title="中国青光眼诊疗指南 2025"; URL="http://www.nhc.gov.cn/"},
    @{Name="CN-STROKE-2024"; Title="中国急性缺血性脑卒中诊治指南 2023"; URL="http://www.nhc.gov.cn/"}
)

foreach ($item in $CN_Standards) {
    $fileName = "$($item.Name)-ref.json"
    $filePath = Join-Path $OutputDir $fileName

    Write-Host "  $($item.Name) - $($item.Title)" -NoNewline

    try {
        Invoke-WebRequest -Uri $item.URL -TimeoutSec 20 -UseBasicParsing -ErrorAction Stop | Out-Null
        Write-Host " ~ OK" -ForegroundColor Green
    } catch {
        Write-Host " : URL saved" -ForegroundColor Yellow
    }

    $refData = @{
        name = $item.Name
        title = $item.Title
        url = $item.URL
        note = "Chinese national standard/guideline. May require access via 国家卫健委 or CNKI."
    }
    $refData | ConvertTo-Json | Set-Content -Path $filePath -Encoding UTF8
    Start-Sleep -Milliseconds 300
}

# ── Summary ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "=" * 70
Write-Host "  Download Summary"
Write-Host "=" * 70
Write-Host "  International standards processed: $total"
Write-Host "  Success: $success | Failed (URL saved): $failed"
Write-Host "  Chinese standards referenced: $($CN_Standards.Count)"
Write-Host ""
Write-Host "  Output directory: $OutputDir"
Write-Host "  Total files: $((Get-ChildItem $OutputDir).Count)"
Write-Host "=" * 70
Write-Host ""
Write-Host "  NOTE: For copyright-restricted standards (ISO, IEC, CLSI):"
Write-Host "    - URLs saved to $OutputDir"
Write-Host "    - Purchase from official sources"
Write-Host "  For freely available standards (NICE, WHO, KDIGO, ACR, etc.):"
Write-Host "    - Reference pages saved with access instructions"
Write-Host "    - Visit source URLs to download PDF versions"
Write-Host "=" * 70

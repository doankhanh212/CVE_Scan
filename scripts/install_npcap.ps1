# Install Npcap on Windows (friendly installer)
# - Elevates to admin when needed
# - Tries winget install first
# - Falls back to opening official Npcap download page
# - Verifies installation via service/registry

param(
    [switch]$Silent
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "[$ts] [$Level] $Message"
}

function Test-IsAdmin {
    try {
        $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
        return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch {
        return $false
    }
}

function Ensure-Admin {
    if (-not (Test-IsAdmin)) {
        Write-Log "Cần quyền Admin để cài Npcap. Đang yêu cầu nâng quyền..." "WARN"
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "powershell.exe"
        $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" + ($(if ($Silent) {" -Silent"} else {""}))
        $psi.Verb = "runas"
        try {
            $proc = [System.Diagnostics.Process]::Start($psi)
            if ($proc -ne $null) {
                Write-Log "Đã mở tiến trình nâng quyền. Vui lòng chấp nhận UAC." "INFO"
                exit 0
            }
        } catch {
            Write-Log "Không thể nâng quyền. Vui lòng chạy PowerShell dưới quyền Admin và chạy lại." "ERROR"
            exit 1
        }
    }
}

function Test-NpcapInstalled {
    # Check service
    try {
        $svc = Get-Service -Name "npcap" -ErrorAction SilentlyContinue
        if ($svc) { return $true }
    } catch {}

    # Check registry
    try {
        $reg = Get-Item -Path "HKLM:\SOFTWARE\Npcap" -ErrorAction SilentlyContinue
        if ($reg) { return $true }
    } catch {}

    # Check common files
    $paths = @(
        "$env:SystemRoot\System32\Npcap\NPFInstall.exe",
        "$env:SystemRoot\System32\drivers\npcap.sys"
    )
    foreach ($p in $paths) { if (Test-Path $p) { return $true } }

    return $false
}

function Install-NpcapViaWinget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Log "Winget không có sẵn. Bỏ qua bước winget." "WARN"
        return $false
    }
    Write-Log "Cài Npcap qua winget..." "INFO"

    # Try common IDs
    $ids = @(
        "Nmap.Npcap",
        "Npcap",
        "Insecure.Npcap" # historical
    )

    foreach ($id in $ids) {
        try {
            Write-Log "Thử cài gói: $id" "INFO"
            $args = @("install", $id, "--silent", "--accept-package-agreements", "--accept-source-agreements")
            $proc = Start-Process -FilePath "winget" -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
            if ($proc.ExitCode -eq 0) {
                Write-Log "Cài đặt qua winget có vẻ thành công." "SUCCESS"
                return $true
            } else {
                Write-Log "winget trả về mã $($proc.ExitCode) cho gói $id" "WARN"
            }
        } catch {
            Write-Log "Lỗi cài winget gói $id: $_" "WARN"
        }
    }
    return $false
}

function Open-NpcapDownloadPage {
    $url = "https://npcap.com/#download"
    Write-Log "Mở trang tải Npcap: $url" "INFO"
    try { Start-Process $url } catch { Write-Log "Không thể mở trình duyệt: $_" "ERROR" }
}

# Main
Write-Log "Bắt đầu cài đặt Npcap" "SYSTEM"
Ensure-Admin

if (Test-NpcapInstalled) {
    Write-Log "Npcap đã được cài đặt." "SUCCESS"
    exit 0
}

$ok = Install-NpcapViaWinget
if (-not $ok) {
    Write-Log "Không cài được qua winget. Mở trang chính thức để tải và cài đặt." "WARN"
    Open-NpcapDownloadPage
    Write-Log "Vui lòng cài đặt thủ công và chạy lại kiểm tra." "INFO"
    exit 2
}

Start-Sleep -Seconds 2
if (Test-NpcapInstalled) {
    Write-Log "Npcap cài đặt thành công." "SUCCESS"
    exit 0
} else {
    Write-Log "Chưa phát hiện Npcap sau khi cài. Có thể cần khởi động lại hoặc cài thủ công." "WARN"
    Open-NpcapDownloadPage
    exit 3
}
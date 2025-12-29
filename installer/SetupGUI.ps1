#requires -version 5.1
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Write-LogUI {
    param(
        [System.Windows.Forms.TextBox]$Box,
        [string]$Message
    )
    if ($Box -and !$Box.IsDisposed) {
        $Box.AppendText("$Message`r`n")
        $Box.ScrollToCaret()
    }
}

function Get-RootDir {
    $scriptPath = $MyInvocation.MyCommand.Path
    $installerDir = Split-Path -Parent $scriptPath
    return Split-Path -Parent $installerDir
}

function Test-Command {
    param([string]$Name)
    try { $null = Get-Command $Name -ErrorAction Stop; return $true } catch { return $false }
}

function Ensure-Python {
    param(
        [System.Windows.Forms.TextBox]$Log
    )
    $pythonOk = (Test-Command 'python') -or (Test-Command 'py')
    if ($pythonOk) {
        Write-LogUI $Log "✓ Python đã có sẵn trên hệ thống"
        return $true
    }
    Write-LogUI $Log "⏳ Python chưa có. Thử cài đặt bằng winget…"
    if (-not (Test-Command 'winget')) {
        Write-LogUI $Log "⚠️ Winget không khả dụng. Vui lòng cài Python thủ công: https://www.python.org/downloads/"
        return $false
    }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'winget'
        $psi.Arguments = 'install -e --id Python.Python'
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($psi)
        $p.WaitForExit()
        if ($p.ExitCode -ne 0) { throw "winget exit code $($p.ExitCode)" }
        Start-Sleep -Seconds 2
        $pythonOk = (Test-Command 'python') -or (Test-Command 'py')
        if ($pythonOk) {
            Write-LogUI $Log "✅ Đã cài đặt Python thành công"
            return $true
        } else {
            Write-LogUI $Log "⚠️ Không tìm thấy lệnh python/py sau khi cài đặt. Hãy khởi động lại PowerShell hoặc cài thủ công."
            return $false
        }
    } catch {
        Write-LogUI $Log "❌ Lỗi cài đặt Python bằng winget: $_"
        return $false
    }
}

function Get-PythonExe {
    # Prefer 'py -3.11', else 'python'
    if (Test-Command 'py') { return 'py -3.11' }
    elseif (Test-Command 'python') { return 'python' }
    elseif (Test-Command 'python3') { return 'python3' }
    else { return $null }
}

function Ensure-Nmap {
    param([System.Windows.Forms.TextBox]$Log)
    if (Test-Command 'nmap') { Write-LogUI $Log "✓ Nmap đã có trong PATH"; return $true }
    Write-LogUI $Log "⏳ Nmap chưa có. Thử cài đặt bằng winget…"
    if (-not (Test-Command 'winget')) {
        Write-LogUI $Log "⚠️ Winget không khả dụng. Vui lòng tải Nmap: https://nmap.org/download"
        return $false
    }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'winget'
        $psi.Arguments = 'install -e --id Nmap.Nmap'
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $p = [System.Diagnostics.Process]::Start($psi)
        $p.WaitForExit()
        if ($p.ExitCode -ne 0) { throw "winget exit code $($p.ExitCode)" }
        Start-Sleep -Seconds 2
        if (Test-Command 'nmap') {
            Write-LogUI $Log "✅ Đã cài đặt Nmap thành công"
            return $true
        } else {
            Write-LogUI $Log "⚠️ Không tìm thấy Nmap trong PATH sau khi cài đặt"
            return $false
        }
    } catch {
        Write-LogUI $Log "❌ Lỗi cài đặt Nmap bằng winget: $_"
        return $false
    }
}

function Setup-VenvAndDeps {
    param([System.Windows.Forms.TextBox]$Log)
    $root = Get-RootDir
    $venv = Join-Path $root 'venv'
    $pyCmd = Get-PythonExe
    if (-not $pyCmd) { Write-LogUI $Log "❌ Không tìm thấy Python để tạo venv"; return $false }
    try {
        Write-LogUI $Log "⏳ Tạo môi trường ảo (venv)…"
        & $pyCmd -m venv $venv | Out-Null
        $venvPy = Join-Path $venv 'Scripts\python.exe'
        if (-not (Test-Path $venvPy)) { Write-LogUI $Log "❌ Không tạo được venv"; return $false }
        Write-LogUI $Log "⏳ Nâng cấp pip…"
        & $venvPy -m pip install --upgrade pip | Out-Null
        $req = Join-Path $root 'requirements.txt'
        if (Test-Path $req) {
            Write-LogUI $Log "⏳ Cài đặt phụ thuộc từ requirements.txt…"
            & $venvPy -m pip install -r $req
        } else {
            Write-LogUI $Log "⚠️ Không tìm thấy requirements.txt"
        }
        return $true
    } catch {
        Write-LogUI $Log "❌ Lỗi khi tạo venv/cài phụ thuộc: $_"
        return $false
    }
}

function Verify-Installation {
    param([System.Windows.Forms.TextBox]$Log)
    $root = Get-RootDir
    $venvPy = Join-Path $root 'venv\Scripts\python.exe'
    $verify = Join-Path $root 'verify_installation.py'
    if (-not (Test-Path $venvPy)) { Write-LogUI $Log "⚠️ Thiếu venv python.exe"; return $false }
    if (-not (Test-Path $verify)) { Write-LogUI $Log "⚠️ Không tìm thấy verify_installation.py"; return $false }
    try {
        Write-LogUI $Log "⏳ Chạy xác minh cài đặt…"
        & $venvPy $verify
        Write-LogUI $Log "✅ Xác minh hoàn tất"
        return $true
    } catch {
        Write-LogUI $Log "❌ Lỗi xác minh: $_"
        return $false
    }
}

# Build GUI
$form = New-Object System.Windows.Forms.Form
$form.Text = 'CVE_Scan - Trình cài đặt'
$form.Size = New-Object System.Drawing.Size(720,540)
$form.StartPosition = 'CenterScreen'
$form.BackColor = [System.Drawing.Color]::FromArgb(11,18,32)

$btn = New-Object System.Windows.Forms.Button
$btn.Text = '🛠 Cài đặt tự động'
$btn.Width = 160
$btn.Height = 34
$btn.Location = New-Object System.Drawing.Point(16,16)
$btn.BackColor = [System.Drawing.Color]::FromArgb(31,41,55)
$btn.ForeColor = [System.Drawing.Color]::White

$help = New-Object System.Windows.Forms.Button
$help.Text = '❔ Hướng dẫn'
$help.Width = 120
$help.Height = 34
$help.Location = New-Object System.Drawing.Point(190,16)
$help.BackColor = [System.Drawing.Color]::FromArgb(31,41,55)
$help.ForeColor = [System.Drawing.Color]::White

$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true
$log.ScrollBars = 'Vertical'
$log.ReadOnly = $true
$log.BackColor = [System.Drawing.Color]::FromArgb(15,23,42)
$log.ForeColor = [System.Drawing.Color]::White
$log.Font = New-Object System.Drawing.Font('Consolas',10)
$log.Location = New-Object System.Drawing.Point(16,64)
$log.Size = New-Object System.Drawing.Size(676,420)

$close = New-Object System.Windows.Forms.Button
$close.Text = 'Đóng'
$close.Width = 100
$close.Height = 30
$close.Location = New-Object System.Drawing.Point(592,16)
$close.BackColor = [System.Drawing.Color]::FromArgb(31,41,55)
$close.ForeColor = [System.Drawing.Color]::White

$form.Controls.AddRange(@($btn,$help,$log,$close))

# Background worker for async install
$bw = New-Object System.ComponentModel.BackgroundWorker
$bw.WorkerReportsProgress = $true
$bw.Add_DoWork({
    param($sender,$e)
    $args = @{ Log = $log }
    Write-LogUI $log 'Bắt đầu cài đặt…'
    if (-not (Ensure-Python @args)) { $e.Result = $false; return }
    if (-not (Setup-VenvAndDeps @args)) { $e.Result = $false; return }
    if (-not (Ensure-Nmap @args)) { Write-LogUI $log '⚠️ Tiếp tục dù thiếu Nmap (sẽ ảnh hưởng quét port)'; }
    if (-not (Verify-Installation @args)) { $e.Result = $false; return }
    $e.Result = $true
})
$bw.Add_RunWorkerCompleted({
    param($sender,$e)
    if ($e.Result -eq $true) {
        Write-LogUI $log '✅ Cài đặt hoàn tất. Bạn có thể chạy ứng dụng.'
    } else {
        Write-LogUI $log '❌ Cài đặt thất bại. Vui lòng xem log ở trên.'
    }
})

$btn.Add_Click({ if (-not $bw.IsBusy) { $bw.RunWorkerAsync() } })
$close.Add_Click({ $form.Close() })
$help.Add_Click({
    try {
        $root = Get-RootDir
        $cand = @(
            (Join-Path $root 'QUICK_REFERENCE_vi.md'),
            (Join-Path $root 'QUICK_REFERENCE.md'),
            (Join-Path $root 'START_HERE_vi.txt'),
            (Join-Path $root 'START_HERE.txt')
        )
        $file = $cand | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($file) {
            Start-Process $file
        } else {
            [System.Windows.Forms.MessageBox]::Show('Không tìm thấy tài liệu hướng dẫn','Hướng dẫn',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Information)
        }
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Lỗi mở hướng dẫn: $_")
    }
})

[void]$form.ShowDialog()

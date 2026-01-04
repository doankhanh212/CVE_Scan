[Setup]
AppName=CVE_Scan
AppVersion=1.0
DefaultDirName={pf}\CVE_Scan
DefaultGroupName=CVE_Scan
OutputBaseFilename=CVE_Scan_Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "build\\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\\config.json"; DestDir: "{app}"
Source: "build\\README.md"; DestDir: "{app}"
; Thêm các file khác nếu cần

[Icons]
Name: "{group}\CVE_Scan"; Filename: "{app}\app.exe"
Name: "{userdesktop}\CVE_Scan"; Filename: "{app}\app.exe"

[Run]
Filename: "{app}\app.exe"; Description: "Chạy CVE_Scan"; Flags: nowait postinstall skipifsilent
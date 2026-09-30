#define MyAppName "Kitchen AI Designer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Kitchen AI"
#define MyAppExeName "KitchenAI.exe"

[Setup]
AppId={{D54DF7C4-8B77-4B55-BE4D-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Kitchen AI Designer
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=KitchenAI_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\KitchenAI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\Kitchen AI Designer"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Kitchen AI Designer"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить Kitchen AI Designer"; Flags: nowait postinstall skipifsilent

; Inno Setup script for Product Image Prompt Builder (Inno Setup 6.3 or newer).
; Run build.bat first (one-folder build), then open this file in Inno Setup and press Compile.
; The installer is written to installer\Output\.

#define MyAppName "Product Image Prompt Builder"
#define MyAppVersion "1.0.0"
#define MyAppExeName "Product Image Prompt Builder.exe"
#define BuildDir "..\dist\Product Image Prompt Builder"

[Setup]
; AppId identifies this app for upgrades/uninstall. Keep it stable between versions.
AppId={{B7C2F1A4-5D3E-4E7B-9C1A-6F2D8E4A9B10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
; {autopf} = "C:\Program Files" on 64-bit Windows.
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=ProductImagePromptBuilder-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Unchecked by default: the desktop shortcut is optional.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut (always) and Desktop shortcut (optional task above).
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; Uninstall: Inno Setup generates the uninstaller automatically ("Apps & features" entry plus
; unins000.exe in the install folder). Per-user settings and logs live in %APPDATA% / %LOCALAPPDATA%
; under "ProductImagePromptBuilder" and are intentionally kept so a reinstall remembers preferences.

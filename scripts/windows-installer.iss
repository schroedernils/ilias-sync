#ifndef AppVersion
  #error AppVersion must be supplied by the native build.
#endif

[Setup]
AppId={{8669D68D-2240-4B64-81E1-40357B3A35BE}
AppName=IliasSync
AppVersion={#AppVersion}
AppPublisher=IliasSync contributors
AppPublisherURL=https://github.com/schroedernils/ilias-sync
AppSupportURL=https://github.com/schroedernils/ilias-sync/issues
AppUpdatesURL=https://github.com/schroedernils/ilias-sync/releases/latest
DefaultDirName={localappdata}\Programs\IliasSync
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=IliasSync-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\build\IliasSync.ico
UninstallDisplayIcon={app}\IliasSync.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\IliasSync\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\IliasSync"; Filename: "{app}\IliasSync.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\IliasSync"; Filename: "{app}\IliasSync.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\IliasSync.exe"; Description: "{cm:LaunchProgram,IliasSync}"; Flags: nowait postinstall skipifsilent

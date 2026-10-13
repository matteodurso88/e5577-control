; Pocket Radio Manager per-user Inno Setup installer.
; Command:
; ISCC.exe /DSourceDir="<frozen onedir>" /DOutputDir="<dist/packages>"
;          /DIconFile="<build/icons/*.ico>" /DAppVersion="0.1.0" thisfile.iss

#ifndef AppVersion
  #error "AppVersion is required"
#endif
#ifndef SourceDir
  #error "SourceDir is required"
#endif
#ifndef OutputDir
  #error "OutputDir is required"
#endif
#ifndef IconFile
  #error "IconFile is required"
#endif

#define AppName "Pocket Radio Manager"
#define AppExe "PocketRadioManager.exe"

[Setup]
AppId={{0B736E83-EA41-4E4D-8BC3-54654FE7E937}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=matteodurso88
AppPublisherURL=https://github.com/matteodurso88/workshop
AppSupportURL=https://github.com/matteodurso88/workshop/issues
AppUpdatesURL=https://github.com/matteodurso88/workshop/releases
DefaultDirName={localappdata}\Programs\Pocket Radio Manager
DefaultGroupName=Pocket Radio Manager
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=pocket-radio-manager-v{#AppVersion}-windows-x86_64-setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
ChangesAssociations=no
UsePreviousAppDir=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Collegamenti"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Pocket Radio Manager"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\Pocket Radio Manager"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Avvia Pocket Radio Manager"; Flags: nowait postinstall skipifsilent

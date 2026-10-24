; E5577 Control per-user Inno Setup installer.
; Command:
; ISCC.exe /DSourceDir="<frozen onedir>" /DOutputDir="<dist/packages>"
;          /DIconFile="<build/icons/*.ico>" /DAppVersion="1.0.1" thisfile.iss

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

#define AppName "E5577 Control"
#define AppExe "E5577Control.exe"

[Setup]
AppId={{0B736E83-EA41-4E4D-8BC3-54654FE7E937}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=matt88.it
AppPublisherURL=https://matt88.it
AppSupportURL=https://github.com/matteodurso88/e5577-control/issues
AppUpdatesURL=https://github.com/matteodurso88/e5577-control/releases
DefaultDirName={localappdata}\Programs\E5577 Control
DefaultGroupName=E5577 Control
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=e5577-control-v{#AppVersion}-windows-x86_64-setup
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
Name: "{autoprograms}\E5577 Control"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\E5577 Control"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Avvia E5577 Control"; Flags: nowait postinstall skipifsilent

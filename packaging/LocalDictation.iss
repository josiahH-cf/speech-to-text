#define MyAppName "Local Dictation"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Local Dictation"
#define MyAppExeName "LocalDictation.exe"

[Setup]
AppId={{6C9EC15F-627D-4669-B5D9-C986181593B3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\LocalDictation
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=LocalDictationSetup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start Local Dictation when I sign in"; GroupDescription: "Startup:"; Flags: unchecked
Name: "bootstrap"; Description: "Prepare speech model and Ollama after install"; GroupDescription: "Setup:"; Flags: checkedonce

[Files]
Source: "..\dist\LocalDictation\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Local Dictation"; Filename: "{app}\{#MyAppExeName}"; Parameters: "run"
Name: "{group}\Settings"; Filename: "{app}\{#MyAppExeName}"; Parameters: "settings"
Name: "{group}\Doctor"; Filename: "{app}\LocalDictationCLI.exe"; Parameters: "doctor"
Name: "{autodesktop}\Local Dictation"; Filename: "{app}\{#MyAppExeName}"; Parameters: "run"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "startup enable"; Flags: runhidden; Tasks: startup
Filename: "{app}\LocalDictationCLI.exe"; Parameters: "setup bootstrap"; Description: "Prepare Local Dictation"; Flags: postinstall; Tasks: bootstrap
Filename: "{app}\{#MyAppExeName}"; Parameters: "run"; Description: "Launch Local Dictation"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "startup disable"; Flags: runhidden

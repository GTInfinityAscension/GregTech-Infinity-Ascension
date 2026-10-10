@echo off
rem GTIA server installer: installs Forge and downloads the CurseForge mods of this release.
rem Needs Java 17+. Run it once from this folder.
setlocal
cd /d "%~dp0"
for /f "tokens=1,2 delims==" %%a in (gtia-installer\versions.txt) do set "GTIA_%%a=%%b"
set "FORGE=%GTIA_minecraft%-%GTIA_forge%"
set "FORGE_JAR=gtia-installer\forge-%FORGE%-installer.jar"
set "BOOT_JAR=gtia-installer\packwiz-installer-bootstrap.jar"

if not exist "%FORGE_JAR%" powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://maven.minecraftforge.net/net/minecraftforge/forge/%FORGE%/forge-%FORGE%-installer.jar' -OutFile '%FORGE_JAR%'"
if not exist "%BOOT_JAR%" powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/packwiz-installer-bootstrap.jar' -OutFile '%BOOT_JAR%'"
powershell -NoProfile -Command "if ((Get-FileHash '%FORGE_JAR%').Hash -ne '75CFCB11F60CC641DC83757C1357C08C9BDBA255EC529FEB115C5E89A59CF75A') { Write-Error 'Forge installer hash mismatch'; exit 1 }" || exit /b 1
powershell -NoProfile -Command "if ((Get-FileHash '%BOOT_JAR%').Hash -ne 'A8FBB24DC604278E97F4688E82D3D91A318B98EFC08D5DBFCBCBCAB6443D116C') { Write-Error 'packwiz-installer-bootstrap hash mismatch'; exit 1 }" || exit /b 1

if not exist run.bat java -jar "%FORGE_JAR%" --installServer
java -jar "%BOOT_JAR%" -g -s server "gtia-installer\pack\pack.toml"
echo Done. Accept the EULA (eula.txt) and start the server with run.bat

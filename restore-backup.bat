@echo off
rem Restores a world from an FTB Backups 2 backup (the backups\ folder of this instance or server).
rem Close Minecraft (or stop the server), then double-click this file or run:
rem   restore-backup.bat            pick a backup from a list
rem   restore-backup.bat FILE.zip   restore that backup
rem The current copy of the world is never deleted: it is renamed to "<world>.before-restore-<date>".
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore-backup.ps1" %*
pause

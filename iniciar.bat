@echo off
rem Doble clic para iniciar la app (evita el bloqueo de scripts de PowerShell).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" %*
if errorlevel 1 pause

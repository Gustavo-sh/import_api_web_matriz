@echo off

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" ^
/v ProxyEnable /t REG_DWORD /d 1 /f >nul 2>&1

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" ^
/v ProxyServer /t REG_SZ /d 192.168.239.14:8080 /f >nul 2>&1

echo Proxy ativado.
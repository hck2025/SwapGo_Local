@echo off
REM SwapGo 런처 단축 실행
REM .pyw 더블클릭과 동일하지만, .bat 으로도 실행 가능하게 둠.
cd /d "%~dp0"
start "" pythonw "swapgo-launcher.pyw"

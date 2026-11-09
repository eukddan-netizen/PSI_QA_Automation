@echo off
set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9333
cd /d "C:\Program Files (x86)\topaegis\PRSv5"
start "" "taKeeper.exe"

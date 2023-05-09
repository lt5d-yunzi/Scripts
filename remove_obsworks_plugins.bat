@echo off
rd /s/q  %APPDATA%\obsplus
set /p filepach=请输入obs studio安装路径，如“C:\Program Files\obs-studio”  
del  /s/q  %filepach%\obs-plugins\64bit\obsplus.dll
echo 文件已删除
pause

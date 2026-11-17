@echo off
setlocal DisableDelayedExpansion
call "C:\Users\Administrator\AppData\Local\Temp\mechdog_vc\vcenv_x64.bat"
if errorlevel 1 exit /b 1
set SDK=D:\Program Files\PTC\Creo 10.0.0.0\Common Files\protoolkit
set ROOT=D:\my\MCP_CREO_MechDog\test_runs\2026-11-17_t1c_closure\probe
cl /nologo /MD /EHsc /std:c++17 /bigobj /W3 /we4552 /DPRO_MACHINE=36 /DPRO_OS=4 /DPRO_USE_VAR_ARGS /I"%SDK%\includes" /I"D:\my\MCP_CREO_MechDog\native" /c "%ROOT%\t1c_surface.cpp" /Fo"%ROOT%\t1c_surface.obj"
if errorlevel 1 exit /b 2
link /nologo /MACHINE:X64 /SUBSYSTEM:CONSOLE /OUT:"%ROOT%\t1c_surface.exe" "%ROOT%\t1c_surface.obj" "%SDK%\x86e_win64\obj\protkmd_NU.lib" "%SDK%\x86e_win64\obj\ptasyncmd.lib" "%SDK%\x86e_win64\obj\ucore.lib" "%SDK%\x86e_win64\obj\udata.lib" bcrypt.lib kernel32.lib user32.lib wsock32.lib advapi32.lib mpr.lib winspool.lib netapi32.lib psapi.lib gdi32.lib shell32.lib comdlg32.lib ole32.lib ws2_32.lib
if errorlevel 1 exit /b 3
exit /b 0

@echo off
setlocal DisableDelayedExpansion
call "C:\Users\Administrator\AppData\Local\Temp\mechdog_vc\vcenv_x64.bat"
if errorlevel 1 exit /b 1
set SDK=D:\Program Files\PTC\Creo 10.0.0.0\Common Files\protoolkit
set ROOT=D:\my\MCP_CREO_MechDog\test_runs\2026-11-17_t1b_id_driven_blend\probe\host
cl /nologo /MD /EHsc /std:c++17 /bigobj /W3 /we4552 /DPRO_MACHINE=36 /DPRO_OS=4 /DPRO_USE_VAR_ARGS /I"%SDK%\includes" /I"D:\my\MCP_CREO_MechDog\native" /c "%ROOT%\probe_host.cpp" /Fo"%ROOT%\probe_host.obj"
if errorlevel 1 exit /b 2
link /nologo /DLL /MACHINE:X64 /OUT:"%ROOT%\probe_host.dll" "%ROOT%\probe_host.obj" "%SDK%\x86e_win64\obj\protk_dllmd_NU.lib" "%SDK%\x86e_win64\obj\ucore.lib" "%SDK%\x86e_win64\obj\udata.lib" kernel32.lib user32.lib wsock32.lib advapi32.lib mpr.lib winspool.lib netapi32.lib psapi.lib gdi32.lib shell32.lib comdlg32.lib ole32.lib ws2_32.lib
if errorlevel 1 exit /b 3
exit /b 0

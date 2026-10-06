@echo off
rem Run this CC's ./cc inside WSL from cmd or PowerShell: cc check, cc verify --quality, ...
rem Uses the default WSL distribution, or the one named in CC_WSL_DISTRO.
setlocal
set "distro="
if defined CC_WSL_DISTRO set "distro=-d %CC_WSL_DISTRO%"
rem The trailing dot keeps the closing quote from being escaped by the path's last backslash.
rem bash -l loads the Nix profile; -e passes the arguments to WSL without another shell.
wsl.exe %distro% --cd "%~dp0." -e bash -lc "exec ./cc \"$@\"" cc %*
exit /b %errorlevel%

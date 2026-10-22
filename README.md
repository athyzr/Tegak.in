# Tegak-in

A Windows desktop application that helps monitor and correct your sitting posture using a webcam.

## Running the Application

Download `Tegak-in.exe` from the **Releases** section and run it on Windows 10/11 (64-bit). No Python installation is required on the user's computer. Allow camera access if prompted by Windows.

If Windows SmartScreen displays an unrecognized file warning, ensure the binary originates from a trusted Tegak-in release before proceeding to run it.

## Building the EXE

The build process runs on Windows and requires 64-bit Python 3.12 along with the Python Launcher (`py`).

1. Open the project folder on Windows.
2. Run `build.bat`.
3. Once completed, the standalone executable will be located at `dist\Tegak-in.exe`.

An active internet connection is required during the initial build to install dependencies. `Tegak-in.exe` is a single-file executable bundled with all necessary dependencies and MediaPipe models. End users do not need Python installed.

To distribute the app, upload `dist\Tegak-in.exe` as a release asset under GitHub Releases. Pushing code updates or commits to the repository will not automatically generate or publish an updated EXE.

Application error logs are stored at `%LOCALAPPDATA%\Tegak-in\error.log`.

# Project: Packaging Ollama in RPM

This project aims to create an **RPM** package for **Ollama**, a local AI assistant, setting it up to run as a service managed by **Systemd**. The resulting RPM package will simplify the installation and management of Ollama on Red Hat/CentOS/Fedora-based systems.

---

## Features

- **RPM Packaging**:
  - Simplifies the installation, removal, and update of Ollama.
  - Includes the pre-compiled Ollama binary.
- **Systemd Service**:
  - Configured to automatically start Ollama on boot.
  - Simplified daemon management with commands like `systemctl start/stop/status/restart`.

---

## Project Structure

- `ollamad.spec`: RPM specification file, defining how the package is built and installed.
- `ollama.service`: Systemd configuration file to manage Ollama as a daemon.
- Binaries and sources:
  - `ollama-linux-amd64.tgz`: Ollama binary for x86_64 systems.
  - `ollama-linux-arm64.tgz`: Ollama binary for ARM64 systems.
  - Additional source code: Obtained from the Ollamad project repository.

---

## TODO List
- Create rocm/cuda packages.
- Separate dependency library downloaded during build.
- Improve spec file.
  - compliance with Fedora's package guidelines.   
  - ~~Create a system user for the Ollama daemon. ~~
  - ~~Change Ollama's home to the `/var` folder. ~~
  - ~~Translate README.md to English.~~

--- 

Let me know if you need further help!
  

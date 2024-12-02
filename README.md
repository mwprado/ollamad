
# Projeto: Empacotamento do Ollama em RPM

Este projeto tem como objetivo criar um pacote **RPM** para o **Ollama**, um assistente de IA local, configurando-o para ser executado como um serviço gerenciado pelo **Systemd**. O pacote RPM resultante facilitará a instalação e o gerenciamento do Ollama em sistemas baseados em Red Hat/CentOS/Fedora.

---

## Funcionalidades

- **Empacotamento em RPM**:
  - Facilita a instalação, remoção e atualização do Ollama.
  - Inclui o binário pré-compilado do Ollama.
- **Serviço Systemd**:
  - Configurado para iniciar o Ollama automaticamente no boot.
  - Gerenciamento simplificado do daemon com comandos como `systemctl start/stop/status/restart`.

---

## Estrutura do Projeto

- `ollamad.spec`: Arquivo de especificação do RPM, definindo como o pacote é construído e instalado.
- `ollama.service`: Arquivo de configuração do Systemd para gerenciar o Ollama como um daemon.
- Binários e fontes:
  - `ollama-linux-amd64.tgz`: Binário do Ollama para sistemas x86_64.
  - `ollama-linux-arm64.tgz`: Binário do Ollama para sistemas ARM64.
  - Código-fonte adicional: Obtido do repositório do projeto Ollamad.

---

## TODO List
- create rocm/cuda packages.
- separate depency library downloaded on build.
- improve spec file.
  - creating a system user for ollama daemon.
  - change ollama's home to var folder.
  - transte README.md to english.
  

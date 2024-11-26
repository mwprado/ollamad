Name:           ollamad
Version:        0.4.5
Release:        1%{?dist}
Summary:        Ollama - AI assistant daemon

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/releases/download/v0.4.5/ollama-linux-amd64.tgz
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip
#Source2:        https://github.com/ollama/ollama/releases/download/v0.4.5/ollama-linux-arm64.tgz


BuildArch:      %{_arch}
Requires:       systemd
BuildRequires: golang

%description
Ollama is a local AI assistant that runs as a daemon. This package installs the Ollama binaries and sets up a Systemd service.

%prep
%autosetup -c -T
%setup -q -n ollama -a 0 -a 1 -a 2

%build
# No compilation required; binaries are precompiled.

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{_unitdir}

# Install binaries
install -m 0755 ollama-linux-amd64 %{buildroot}/usr/bin/ollama

# Install Systemd service file
install -Dm644 ollama.service %{buildroot}%{_unitdir}/ollama.service

%files
%license LICENSE
%doc README.md
/usr/bin/ollama
%{_unitdir}/ollama.service

%changelog
* Wed Nov 26 2024 Maintainer <email@example.com> - 0.4.5-1
- Initial RPM packaging.


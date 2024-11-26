Name:           ollamad
Version:        0.4.5
Release:        1%{?dist}
Summary:        Ollama - AI assistant daemon

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{Version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildArch:      %{_arch}
Requires:       systemd
BuildRequires: golang

%description
Ollama is a local AI assistant that runs as a daemon. This package installs the Ollama binaries and sets up a Systemd service.

%prep
%setup -q -n ollama-0.4.5 -a 1

%build
# Compile the source code for Ollama
cd %{_builddir}/ollama-0.4.5
make
go build

%install
# Install Ollama binary
install -Dm0755 %{_builddir}/ollama-0.4.5/bin/ollama %{buildroot}/usr/bin/ollama

# Install Ollamad binary
install -Dm0755 %{_builddir}/ollamad-main/bin/ollamad %{buildroot}/usr/bin/ollamad

# Install Systemd service file
install -Dm0644 %{_builddir}/ollamad-main/ollama.service %{buildroot}%{_unitdir}/ollama.service

%files
%license LICENSE
%doc README.md
/usr/bin/ollama
/usr/bin/ollamad
%{_unitdir}/ollama.service

%post
# Reload Systemd daemon to recognize the service
systemctl daemon-reload

%preun
if [ $1 -eq 0 ]; then
    systemctl stop ollama.service || true
    systemctl disable ollama.service || true
fi

%postun
if [ $1 -eq 0 ]; then
    systemctl daemon-reload
fi

%changelog
* Wed Nov 26 2024 Maintainer <email@example.com> - 0.4.5-1
- Initial RPM packaging with source compilation.


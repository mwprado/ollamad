Name:           ollama
Version:        0.4.6
Release:        %autorelease
Summary:        Ollama - AI assistant daemon

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildArch:      %{_arch}
Requires:       systemd
BuildRequires:  systemd
BuildRequires:  golang
BuildRequires:  git
BuildRequires:  gcc-c++

%description
Ollama is a local AI assistant that runs as a daemon. This package installs the Ollama binaries and sets up a Systemd service.

%prep
%setup
%setup -T -D -a 1


%build
# Compile the source code for Ollama
make -C %{_builddir}/ollama-%{version}
go build

%install
# Install Ollama binary
install -Dm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_sbindir}/ollama

# Install Systemd service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service

# Install Config  Systemd Service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad.conf

# creating models folder
mkdir -p %{buildroot}%{_datadir}/ollama/models

%files
%license LICENSE
%doc README.md
%{_sbindir}/ollama
%{_unitdir}/ollamad.service
%config(noreplace) %{_sysconfdir}/ollamad.conf
%{_datadir}/ollama/models

%post
# Reload Systemd daemon to recognize the service
systemctl daemon-reload

%preun
if [ $1 -eq 0 ]; then
    systemctl stop ollamad.service || true
    systemctl disable ollamad.service || true
fi

%postun
if [ $1 -eq 0 ]; then
    systemctl daemon-reload
fi

%changelog
%autochangelog

Name:           ollama
Version:        0.5.12
Release:        %autorelease
Summary:        AI assistant daemon

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildArch:      %{_arch}
	
Requires(pre): /usr/sbin/useradd, /usr/bin/getent
Requires:       systemd
BuildRequires:  systemd
BuildRequires:  golang
BuildRequires:  git
BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  ccache

%description
Ollama is a local AI assistant that runs as a daemon.

%prep
%setup
%setup -T -D -a 1

%build
# Compile the source code for Ollama
#make -C %{_builddir}/ollama-%{version}
cmake -B %{_builddir}/ollama-%{version}
cmake --build %{_builddir}/ollama-%{version}
go build

%install
# Install Ollama binary
install -Dm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Install Systemd service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service

# Install Config  Systemd Service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.conf    %{buildroot}%{_sysconfdir}/ollama/ollamad.conf

install -Dm0644 %{_builddir}/ollama-%{version}/%{_libdir}/ollama/libggml-base.so %{buildroot}%{_libdir}/ollama/libggml-base.so
install -Dm0644 %{_builddir}/ollama-%{version}/%{_libdir}/ollama/libggml-cpu-alderlake.so %{buildroot}%{_libdir}/ollama/libggml-cpu-alderlake.so
install -Dm0644 %{_builddir}/ollama-%{version}/%{_libdir}/ollama/libggml-cpu-haswell.so %{buildroot}%{_libdir}/ollama/libggml-cpu-haswell.so
install -Dm0644 %{_builddir}/ollama-%{version}/%{_libdir}/ollama/libggml-cpu-icelake.so %{buildroot}%{_libdir}/ollama/libggml-cpu-icelake.so
install -Dm0644 %{_builddir}/ollama-%{version}/%{_libdir}/ollama/libggml-cpu-sandybridge.so %{buildroot}%{_libdir}/ollama/libggml-cpu-sandybridge.so
install -Dm0644 %{_builddir}/ollama-%{version}/%{_libdir}/ollama/libggml-cpu-sapphirerapids.so %{buildroot}%{_libdir}/ollama/libggml-cpu-sapphirerapids.so
           
%files
%defattr(-,root,root)
%license LICENSE
%doc README.md
%{_bindir}/ollama
%{_unitdir}/ollamad.service
%{_libdir}/ollama/libggml-base.so
%{_libdir}/ollama/libggml-cpu-alderlake.so
%{_libdir}/ollama/libggml-cpu-haswell.so
%{_libdir}/ollama/libggml-cpu-icelake.so
%{_libdir}/ollama/libggml-cpu-sandybridge.so
%{_libdir}/ollama/libggml-cpu-sapphirerapids.so
%{_libdir}/ollama/libggml-cpu-skylakex.so

%config(noreplace) %{_sysconfdir}/ollama/ollamad.conf
%dir %{_sysconfdir}/ollama

%post
ldconfig
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

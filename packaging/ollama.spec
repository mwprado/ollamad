Name:           ollama
Version:        0.12.5
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
export PATH=$PATH:/usr/local/cuda/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64:/usr/local/cuda/extras/CUPTI/lib64
export CUDACXX=/usr/local/cuda/bin/nvcc
export GIN_MODE=release
# Compile the source code for Ollama
cmake -B %{_builddir}/ollama-%{version}  -DCUDAToolkit_ROOT=/usr/local/cuda/ -DCUDACXX=/usr/local/cuda/bin/nvcc -DGIN_MODE=release -DGGML_CCACHE=OFF
cmake --build %{_builddir}/ollama-%{version}
go build

%install
# Install Ollama binary
install -Dm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Install Systemd service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service

# Install Config  Systemd Service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.conf    %{buildroot}%{_sysconfdir}/ollama/ollamad.conf
           
%files
%defattr(-,root,root)
%license LICENSE
%doc README.md
%{_bindir}/ollama
%{_unitdir}/ollamad.service

%config(noreplace) %{_sysconfdir}/ollama/ollamad.conf
%dir %{_sysconfdir}/ollama

%post
#ldconfig
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

Name:           ollama
Version:        0.12.6
Release:        %autorelease
Summary:        AI assistant daemon

License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildArch:      %{_arch}
	
Requires(pre): /usr/sbin/useradd, /usr/bin/getent
Requires:       systemd
Requires:       vulkan
Requires:       vulkan-loader 
Requires:       vulkan-tools
Requires:       glslc
Requires:       glslang

BuildRequires:  systemd
BuildRequires:  golang
BuildRequires:  git
BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  ccache

BuildRequires:  vulkan-tools
BuildRequires:  vulkan-headers
BuildRequires:  vulkan-loader-devel
BuildRequires:  vulkan-validation-layers
BuildRequires:  glslc
BuildRequires:  glslang

%description
Ollama is a local AI assistant that runs as a daemon.

%pre
getent group ollama >/dev/null || groupadd -r ollama
getent passwd ollama >/dev/null || useradd -r -g ollama -d %{_sharedstatedir}/ollama -s /sbin/nologin ollama

%prep
%setup
%setup -T -D -a 1

%build

# CPU libraries
#cmake --preset CPU
#cmake --build --parallel --preset CPU
#cmake --install build --component CPU --strip

# Vulkan libraries
#cmake --preset Vulkan
#cmake --build --parallel --preset Vulkan
#cmake --install build --component Vulkan --strip

cmake -B %{_builddir}/ollama-%{version} --preset Vulkan
cmake --build %{_builddir}/ollama-%{version}
go build

%install
# Install Ollama binary
install -Dm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Install Systemd service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service

# Install Config  Systemd Service file
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.conf    %{buildroot}%{_sysconfdir}/ollama/ollamad.conf

mkdir -p %{buildroot}%{_sharedstatedir}/ollama

%files
%defattr(-,root,root,-)
%license LICENSE
%doc README.md
%{_bindir}/ollama
%{_unitdir}/ollamad.service

%attr(775, ollama, ollama) %dir %{_sysconfdir}/ollama
%dir %attr(775, ollama, ollama)  %{_sharedstatedir}/ollama
%config(noreplace) %attr(640, ollama, ollama) %{_sysconfdir}/ollama/ollamad.conf


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

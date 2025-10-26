Name:           ollama
Version:        0.12.6
Release:        %autorelease
Summary:        AI assistant daemon

License:        MIT
URL:            https://github.com/ollama/ollama

# Upstream e pacote auxiliar com arquivos (service, conf, libs)
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildArch:      %{_arch}

Requires(pre):  /usr/sbin/useradd, /usr/bin/getent
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
BuildRequires:  patchelf

%description
Ollama is a local AI assistant that runs as a daemon.

%pre
getent group ollama >/dev/null || groupadd -r ollama
getent passwd ollama >/dev/null || useradd -r -g ollama -d %{_sharedstatedir}/ollama -s /sbin/nologin ollama

%prep
# Fonte principal (upstream)
%setup
# Fonte auxiliar (seus artefatos)
%setup -T -D -a 1

%build
# Build Vulkan como no seu spec (ajuste conforme sua pipeline)
cmake -B %{_builddir}/ollama-%{version} --preset Vulkan
cmake --build %{_builddir}/ollama-%{version}
# Binário Go
go build

%install
# Binário
install -Dm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Service e conf vindos do Source1
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollama/ollamad.conf
install -Dm0644 %{_builddir}/ollama-%{version}/ollamad-main/ollamad-ld.conf %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollama-ld.conf

# Diretórios de estado
install -d %{buildroot}%{_sharedstatedir}/ollama

# === libs ggml ===
install -d %{buildroot}%{_libdir}/ollama
# ATENÇÃO: caminho corrigido para ollamad-main/ollama/lib/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-base.so           %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-alderlake.so   %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-haswell.so     %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-icelake.so     %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-sandybridge.so %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-skylakex.so    %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-sse42.so       %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cpu-x64.so         %{buildroot}%{_libdir}/ollama/
#install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-cuda.so            %{buildroot}%{_libdir}/ollama/
install -m0755 %{_builddir}/ollama-%{version}/lib/ollama/libggml-vulkan.so          %{buildroot}%{_libdir}/ollama/

# --- Corrige RPATH/RUNPATH para evitar erros 0002 e 0010 ---
for f in %{buildroot}%{_libdir}/ollama/*.so; do
    patchelf --remove-rpath "$f" || :
    patchelf --set-rpath '$ORIGIN' "$f"
done


%files
%defattr(-,root,root,-)
%license LICENSE
%doc README.md

%{_bindir}/ollama
%{_unitdir}/ollamad.service

%attr(775, ollama, ollama) %dir %{_sysconfdir}/ollama
%dir %attr(775, ollama, ollama) %{_sharedstatedir}/ollama
%config(noreplace) %attr(640, ollama, ollama) %{_sysconfdir}/ollama/ollamad.conf

%dir %{_libdir}/ollama
%{_libdir}/ollama/libggml-base.so
%{_libdir}/ollama/libggml-cpu-alderlake.so
%{_libdir}/ollama/libggml-cpu-haswell.so
%{_libdir}/ollama/libggml-cpu-icelake.so
%{_libdir}/ollama/libggml-cpu-sandybridge.so
%{_libdir}/ollama/libggml-cpu-skylakex.so
%{_libdir}/ollama/libggml-cpu-sse42.so
%{_libdir}/ollama/libggml-cpu-x64.so
%{_libdir}/ollama/libggml-cuda.so
%{_libdir}/ollama/libggml-vulkan.so

%post
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

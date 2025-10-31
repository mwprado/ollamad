# Base SPEC sem CUDA: inclui CPU + ROCm + Vulkan
Name:           ollama
Version:        0.12.7
Release:        2%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.tar.gz#/ollama-%{version}.tar.gz

# Auxiliares
Source10:       packaging/ollamad.sysusers
Source11:       packaging/ollamad.service
Source12:       packaging/ollamad.conf
Source13:       packaging/ollamad-ld.conf

# Build deps (sem CUDA aqui)
BuildRequires:  golang
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  systemd-rpm-macros
BuildRequires:  patchelf
# Vulkan opcional
# BuildRequires:  vulkan-headers
# BuildRequires:  vulkan-loader-devel
# ROCm opcional (headers/libs de desenvolvimento, conforme repo)
# BuildRequires:  rocm-hip-sdk
# BuildRequires:  rocm-opencl

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%package -n ollama
Summary:  Ollama (CPU)
%description -n ollama
Ollama (CPU).

%package -n ollama-rocm
Summary:  ROCm runners for Ollama (AMD)
Requires: ollama = %{version}-%{release}
%description -n ollama-rocm
Runners ROCm/AMD (se gerados pelo build) instalados em %{_libdir}/ollama.

%package -n ollama-vulkan
Summary:  Vulkan runners for Ollama
Requires: ollama = %{version}-%{release}
%description -n ollama-vulkan
Runners Vulkan (se gerados pelo build) instalados em %{_libdir}/ollama.

%prep
%autosetup -n ollama-%{version}

%build
case "%{_arch}" in
  x86_64)  export GOARCH=amd64 ;;
  aarch64) export GOARCH=arm64 ;;
  *) echo "Arquitetura não suportada: %{_arch}"; exit 1 ;;
esac
export GOOS=linux
export CGO_ENABLED=1
export GOFLAGS="-buildvcs=false -trimpath"

# Gera dist sem CUDA; pode habilitar ROCm/Vulkan se toolchains existirem
%make_build dist || :
# %make_build dist ROCM=1 || :
# %make_build dist VULKAN=1 || :
go build -ldflags "-s -w" -o ollama ./cmd/ollama

%install
rm -rf %{buildroot}
install -Dpm0755 ollama %{buildroot}%{_bindir}/ollama
install -d %{buildroot}%{_libdir}/ollama

# CPU
if [ -d "dist/linux-$GOARCH/lib/ollama" ]; then
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-base.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-cpu-*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
fi

# ROCm (se presentes)
cp -a dist/linux-$GOARCH/lib/ollama/*rocm*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*hip*.so  %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*opencl*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# Vulkan (se presentes)
cp -a dist/linux-$GOARCH/lib/ollama/*vulkan*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*vk*.so     %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# limpar RPATH
if ls %{buildroot}%{_libdir}/ollama/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{_libdir}/ollama/*.so; do patchelf --remove-rpath "$so" || true; done
fi

install -Dpm0644 %{SOURCE11} %{buildroot}%{_unitdir}/ollamad.service
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf
install -Dpm0644 %{SOURCE10} %{buildroot}%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%pre -n ollama
%if 0%{?__systemd_sysusers:1}
%sysusers_create_compat %{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%endif
exit 0

%post -n ollama
%ldconfig
%systemd_post ollamad.service

%preun -n ollama
%systemd_preun ollamad.service

%postun -n ollama
%ldconfig
%systemd_postun_with_restart ollamad.service

%files -n ollama
%license LICENSE*
%doc README* docs/*
%{_bindir}/ollama
%{_libdir}/ollama/libggml-base.so
%{_libdir}/ollama/libggml-cpu-*.so
%{_unitdir}/ollamad.service
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf
%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf

%files -n ollama-rocm
%{_libdir}/ollama/*rocm*.so
%{_libdir}/ollama/*hip*.so
%{_libdir}/ollama/*opencl*.so
%{_libdir}/ollama/rocblas*/library/*

%files -n ollama-vulkan
%{_libdir}/ollama/*vulkan*.so
%{_libdir}/ollama/*vk*.so

%changelog
* Thu Oct 30 2025 Moacyr <you@example.org> - 0.12.6-2
- Split: removido CUDA deste SPEC; CUDA vai para SPEC separado (RPM Fusion)

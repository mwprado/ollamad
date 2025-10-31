Name:           ollama
Version:        0.12.7
Release:        4%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Fontes (ZIP)

# Arquivos auxiliares (ROOT das SOURCES)

BuildRequires:  golang
BuildRequires:  vulkan-headers
BuildRequires:  pkgconfig
BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  systemd-rpm-macros
BuildRequires:  patchelf
BuildRequires:  unzip

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

# ==================== PACOTE BASE (implícito por Name:) ====================
%description
Ollama (CPU). Inclui o binário principal, runners CPU, serviço systemd (ollamad.service),
sysusers, arquivo de ambiente em /etc/ollamad e ld.so.conf.d para %{_libdir}/ollama.

# ==================== SUBPACOTES ====================
%package -n ollama-vulkan
Summary:  Vulkan runners for Ollama
Requires: ollama = %{version}-%{release}

%description -n ollama-vulkan
Bibliotecas/runners com suporte a Vulkan para o Ollama (instaladas em %{_libdir}/ollama).

%package -n ollama-opencl
Summary:  OpenCL runners for Ollama
Requires: ollama = %{version}-%{release}

%description -n ollama-opencl
Bibliotecas/runners com suporte a OpenCL para o Ollama (instaladas em %{_libdir}/ollama).

%package -n ollama-rocm
Summary:  ROCm/HIP runners for Ollama (AMD)
Requires: ollama = %{version}-%{release}

%description -n ollama-rocm
Bibliotecas/runners com suporte a ROCm/HIP para o Ollama (instaladas em %{_libdir}/ollama).
Inclui, quando presente, a árvore rocBLAS/libraries embalada pelo upstream.

# ==================== PREP/BUILD ====================
%prep
%setup -q -n ollama-%{version} -a 1

%build
case "%{_arch}" in
  x86_64)  export GOARCH=amd64 ;;
  aarch64) export GOARCH=arm64 ;;
  *) echo "Arquitetura não suportada: %{_arch}"; exit 1 ;;
esac

export GOOS=linux
export CGO_ENABLED=1
export GOFLAGS="-buildvcs=false -trimpath"

# Compile all desired presets; tolerate missing ones
for preset in CPU Vulkan OpenCL ROCm; do
  echo "===> Compilando preset: $preset"
  cmake --preset "$preset" -B %{_builddir}/ollama-%{version}-$preset || :
  cmake --build %{_builddir}/ollama-%{version}-$preset -j%{?_smp_build_ncpus} || :
done

# Binário Go principal
go build -ldflags "-s -w" -o ollama ./cmd/ollama

%install
rm -rf %{buildroot}
install -Dpm0755 ollama %{buildroot}%{_bindir}/ollama
install -d %{buildroot}%{_libdir}/ollama

# CPU (base)
if [ -d "dist/linux-$GOARCH/lib/ollama" ]; then
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-base.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-cpu-*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
fi

# Vulkan (subpackage)
cp -a dist/linux-$GOARCH/lib/ollama/*vulkan*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*vk*.so     %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# OpenCL (subpackage)
cp -a dist/linux-$GOARCH/lib/ollama/*opencl*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# ROCm/HIP (subpackage)
cp -a dist/linux-$GOARCH/lib/ollama/*rocm*.so   %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*hip*.so    %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/rocblas*/library/* %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# Strip RPATH/RUNPATH
if ls %{buildroot}%{_libdir}/ollama/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{_libdir}/ollama/*.so; do patchelf --remove-rpath "$so" || true; done
fi

# systemd/sysusers/config/ld.so.conf.d
install -Dpm0644 ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 ollamad-main/ollamad.sysusers %{buildroot}%{_sysusersdir}/ollamad.conf
install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf
install -Dpm0644 ollamad-main/ollamad-ld.conf %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

# ==================== SCRIPTS ====================
%pre
%if 0%{?__systemd_sysusers:1}
%sysusers_create_compat %{_sysusersdir}/ollamad.conf
%endif
exit 0

%post
%ldconfig
%systemd_post ollamad.service

%preun
%systemd_preun ollamad.service

%postun
%ldconfig
%systemd_postun_with_restart ollamad.service

# ==================== FILES ====================
# Base
%files
%license LICENSE*
%doc README* docs/*
%{_bindir}/ollama
%{_libdir}/ollama/libggml-base.so
%{_libdir}/ollama/libggml-cpu-*.so
%{_unitdir}/ollamad.service
%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

# Vulkan
%files -n ollama-vulkan
%{_libdir}/ollama/*vulkan*.so
%{_libdir}/ollama/*vk*.so

# OpenCL
%files -n ollama-opencl
%{_libdir}/ollama/*opencl*.so

# ROCm
%files -n ollama-rocm
%{_libdir}/ollama/*rocm*.so
%{_libdir}/ollama/*hip*.so
%{_libdir}/ollama/rocblas*/library/*

%changelog
* Thu Oct 30 2025 Moacyr <you@example.org> - 0.12.6-4
- Fix: proper subpackage description tags (`%description -n <name>`)
- Base package uses implicit Name: (no `%package -n ollama`)

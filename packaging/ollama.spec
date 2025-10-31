Name:           ollama
Version:        0.12.7
Release:        2%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildRequires:  golang
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig
BuildRequires:  vulkan-headers
BuildRequires:  patchelf
BuildRequires:  unzip

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

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

%prep
%setup -q -n ollama-%{version} -a 1

%check
# Confere Source1 (ollamad-main) e arquivos necessários
test -d ollamad-main
test -f ollamad-main/ollamad.service
test -f ollamad-main/ollamad.sysusers
test -f ollamad-main/ollamad.conf
test -f ollamad-main/ollamad-ld.conf
# Opcional: CMake presets
test -f CMakePresets.json || true

%build
case "%{_arch}" in
  x86_64)  export GOARCH=amd64 ;;
  aarch64) export GOARCH=arm64 ;;
  *) echo "Arquitetura não suportada: %{_arch}"; exit 1 ;;
esac

export GOOS=linux
export CGO_ENABLED=1
export GOFLAGS="-buildvcs=false -trimpath"

SRCDIR=%{_builddir}/ollama-%{version}

# Compila todos os presets; tolera ausência de algum com "|| :"
for preset in CPU Vulkan OpenCL ROCm; do
  echo "===> Compilando preset: $preset"
  cmake -S "$SRCDIR" --preset "$preset" -B %{_builddir}/ollama-%{version}-$preset || :
  cmake --build %{_builddir}/ollama-%{version}-$preset -j%{?_smp_build_ncpus} || :
done

# Binário Go a partir do SRCDIR
mkdir -p %{_builddir}/ollama-%{version}
( cd "$SRCDIR" && go build -ldflags "-s -w" -o %{_builddir}/ollama-%{version}/ollama .)

%install
rm -rf %{buildroot}

# Instala o binário construído
install -Dpm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Diretório de libs dos runners
install -d %{buildroot}%{_libdir}/ollama

# Coleta artefatos dos diretórios dos presets e do dist/ clássico
for d in \
  "%{_builddir}/ollama-%{version}-CPU/dist/linux-$GOARCH/lib/ollama" \
  "%{_builddir}/ollama-%{version}-Vulkan/dist/linux-$GOARCH/lib/ollama" \
  "%{_builddir}/ollama-%{version}-OpenCL/dist/linux-$GOARCH/lib/ollama" \
  "%{_builddir}/ollama-%{version}-ROCm/dist/linux-$GOARCH/lib/ollama" \
  "dist/linux-$GOARCH/lib/ollama"
do
  [ -d "$d" ] || continue
  # CPU (base)
  cp -a "$d"/libggml-base.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a "$d"/libggml-cpu-*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  # Vulkan (subpackage)
  cp -a "$d"/*vulkan*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a "$d"/*vk*.so     %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  # OpenCL (subpackage)
  cp -a "$d"/*opencl*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  # ROCm/HIP (subpackage)
  cp -a "$d"/*rocm*.so   %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a "$d"/*hip*.so    %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a "$d"/rocblas*/library/* %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
done

# Sanitiza RPATH/RUNPATH
if ls %{buildroot}%{_libdir}/ollama/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{_libdir}/ollama/*.so; do
    patchelf --remove-rpath "$so" || true
  done
fi

# Instala systemd/sysusers/config/ld.so.conf.d do Source1 (ollamad-main)
install -Dpm0644 ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 ollamad-main/ollamad.sysusers %{buildroot}%{_sysusersdir}/ollamad.conf

install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf

install -Dpm0644 ollamad-main/ollamad-ld.conf %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

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
* Fri Oct 31 2025 Moacyr <you@example.org> - 0.12.7-1
- Ajusta build com CMake presets (CPU, Vulkan, OpenCL, ROCm) e Go a partir do SRCDIR
- Coleta artefatos dos diretórios de build dos presets
- Usa Source1 (ollamad-main) para service/sysusers/config no %%install

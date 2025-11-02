Name:           ollama
Version:        0.12.8
Release:        7%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Fallbacks de paths
%{!?_unitdir:%global _unitdir /usr/lib/systemd/system}
%{!?_sysusersdir:%global _sysusersdir /usr/lib/sysusers.d}

# Sempre instalar em /usr/lib/ollama (mesmo em x86_64)
%global ollama_libdir /usr/lib/ollama

# Habilite/desabilite subpacotes GPU conforme desejar
%bcond_without vulkan
%bcond_without rocm
# OpenCL fica fora (sem preset/documentação estável)
%bcond_with opencl

# Fontes
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

# Requisitos de build
BuildRequires:  golang
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  pkgconfig
BuildRequires:  patchelf
BuildRequires:  chrpath
BuildRequires:  unzip
BuildRequires:  systemd-rpm-macros
# Para Vulkan presets (ajuste conforme chroot)
%if %{with vulkan}
BuildRequires:  vulkan-headers
#BuildRequires:  glslc
#BuildRequires:  glslang
%endif
# Para ROCm (ajuste conforme disponibilidade COPR/Mock)
%if %{with rocm}
#BuildRequires:  rocm-devel
#BuildRequires:  hip-devel
%endif

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%description
Ollama. Empacota seguindo o fluxo do Dockerfile oficial:
- CMake presets por componente (CPU, Vulkan, ROCm/HIP) com 'cmake --install ... --component ...'
- Binário Go compilado com -buildmode=pie
- Systemd (ollamad.service), sysusers, configuração em /etc/ollamad
- ld.so.conf.d apontando /usr/lib/ollama

# --------- Subpacotes ----------
%if %{with vulkan}
%package -n ollama-vulkan
Summary: Vulkan runners for Ollama
Requires: ollama = %{version}-%{release}

%description -n ollama-vulkan
Runners/Bibliotecas Vulkan do Ollama (instaladas em %{ollama_libdir}).
%endif

%if %{with rocm}
%package -n ollama-rocm
Summary: ROCm/HIP runners for Ollama (AMD)
Requires: ollama = %{version}-%{release}

%description -n ollama-rocm
Runners/Bibliotecas ROCm/HIP do Ollama (instaladas em %{ollama_libdir}).
Inclui bibliotecas rocBLAS conforme instaladas pelo componente HIP.
%endif

%prep
%setup -q -n ollama-%{version} -a 1

%check
# Garante que Source1 trouxe os artefatos de serviço/config
test -d ollamad-main
test -f ollamad-main/ollamad.service
test -f ollamad-main/ollamad.sysusers
test -f ollamad-main/ollamad.conf
# CMakePresets.json pode ou não existir; presets são esperados no upstream
test -f CMakePresets.json || true

%build
# GOARCH
case "%{_arch}" in
  x86_64)  export GOARCH=amd64 ;;
  aarch64) export GOARCH=arm64 ;;
  *) echo "Arquitetura não suportada: %{_arch}"; exit 1 ;;
esac

export GOOS=linux
export CGO_ENABLED=1
export GOFLAGS="-buildvcs=false -trimpath"
export CMAKE_BUILD_PARALLEL_LEVEL=%{?_smp_build_ncpus}
export PARALLEL=%{?_smp_build_ncpus}

SRCDIR=%{_builddir}/ollama-%{version}
# Diretório de staging onde "cmake --install --component" vai depositar /usr/*
STAGING=%{_builddir}/staging-%{version}-%{_arch}
# Binário Go fora do SRCDIR
GOBINDIR=%{_builddir}/go-ollama-%{version}-%{_arch}

rm -rf "$STAGING" "$GOBINDIR"
mkdir -p "$STAGING" "$GOBINDIR"

pushd "$SRCDIR"
# ====== CPU (sempre) ======
rm -rf build
cmake --preset "CPU"
cmake --build --parallel ${PARALLEL} --preset "CPU"
DESTDIR="$STAGING" cmake --install build --component CPU --strip --parallel ${PARALLEL}

# ====== Vulkan (opcional) ======
%if %{with vulkan}
rm -rf build
cmake --preset "Vulkan" -DOLLAMA_RUNNER_DIR="vulkan"
cmake --build --parallel ${PARALLEL} --preset "Vulkan"
DESTDIR="$STAGING" cmake --install build --component Vulkan --strip --parallel ${PARALLEL}
%endif

# ====== ROCm 6 (opcional / HIP) ======
%if %{with rocm}
rm -rf build
cmake --preset "ROCm 6" -DOLLAMA_RUNNER_DIR="rocm"
cmake --build --parallel ${PARALLEL} --preset "ROCm 6"
DESTDIR="$STAGING" cmake --install build --component HIP --strip --parallel ${PARALLEL}
# Limpeza de blobs gfx90[06], equivalente ao Dockerfile
rm -f "$STAGING"/usr/lib/ollama/rocm/rocblas/library/*gfx90[06]*
%endif
popd

# ====== Binário Go (igual ao Docker, fora do SRCDIR) ======
( cd "$SRCDIR" && \
  if [ -f main.go ]; then \
    go build -trimpath -buildmode=pie -ldflags "-s -w" -o "$GOBINDIR/ollama" . ; \
  else \
    go build -trimpath -buildmode=pie -ldflags "-s -w" -o "$GOBINDIR/ollama" ./cmd/ollama ; \
  fi )

%install
rm -rf %{buildroot}

# Instala binário
install -Dpm0755 %{_builddir}/go-ollama-%{version}-%{_arch}/ollama %{buildroot}%{_bindir}/ollama

# Copia todo conteúdo instalado via DESTDIR="$STAGING" (prefix=/usr)
# Isso inclui os componentes CPU e, se habilitados, Vulkan e HIP (ROCm).
if [ -d "%{_builddir}/staging-%{version}-%{_arch}/usr" ]; then
  cp -a %{_builddir}/staging-%{version}-%{_arch}/usr/* %{buildroot}/usr/
fi

# QA Fedora: limpa RPATH/RUNPATH nas .so colocadas em /usr/lib/ollama
if ls %{buildroot}%{ollama_libdir}/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{ollama_libdir}/*.so; do
    chrpath -d "$so" 2>/dev/null || true
    patchelf --remove-rpath "$so" 2>/dev/null || true
  done
fi

# systemd / sysusers / configuração
install -Dpm0644 ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 ollamad-main/ollamad.sysusers %{buildroot}%{_sysusersdir}/ollamad.conf
install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf

# ld.so.conf.d -> /usr/lib/ollama
install -d %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{ollama_libdir}" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

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

# ---------- ARQUIVOS ----------
%files
%license LICENSE*
%doc README.md
%doc docs/*
%{_bindir}/ollama
%{_unitdir}/ollamad.service
%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

%if %{with vulkan}
%files -n ollama-vulkan
%{ollama_libdir}/*vulkan*.so
%{ollama_libdir}/*vk*.so
%endif

%if %{with rocm}
%files -n ollama-rocm
%{ollama_libdir}/*rocm*.so
%{ollama_libdir}/*hip*.so
%{ollama_libdir}/rocm/rocblas/library/*
%endif

%changelog
* Sun Nov 02 2025 Moacyr Prado <you@example.org> - 0.12.7-7
- Alinha ao Dockerfile oficial: presets CPU/Vulkan/ROCm6 com install por component (CPU/Vulkan/HIP)
- Usa staging DESTDIR e copia para buildroot no %install
- Compila Go com -buildmode=pie; mantém systemd/sysusers/conf/ldconfig
- Subpacotes -vulkan e -rocm ligados via bconds

Name:           ollama
Version:        0.12.7
Release:        6%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Paths/macros (fallbacks)
%{!?_unitdir:%global _unitdir /usr/lib/systemd/system}
%{!?_sysusersdir:%global _sysusersdir /usr/lib/sysusers.d}
# Destino único para as libs (força /usr/lib mesmo em x86_64)
%global ollama_libdir %{_prefix}/lib/ollama

# Subpacotes opcionais (habilitados por padrão onde existirem artefatos)
%bcond_without vulkan
%bcond_without rocm
# OpenCL permanece desabilitado (sem preset/documentação estável)
%bcond_with opencl

# Fontes conforme sua orientação
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
BuildRequires:  chrpath
BuildRequires:  unzip
BuildRequires:  systemd-rpm-macros
# Dependências comuns para Vulkan/ROCm (ajuste conforme seu chroot)
# BuildRequires:  glslc glslang
# BuildRequires:  rocm-devel

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%description
Ollama. Compila o binário principal e gera/liga os backends dinâmicos de GPU
(Vulkan/ROCm) em um único build (seguindo a documentação oficial: cmake -> build -> go build).
Instala serviço systemd (ollamad.service), sysusers, arquivo de ambiente em
/etc/ollamad e registra %{ollama_libdir} no ldconfig.

# ---------- Subpackages ----------
%if %{with vulkan}
%package -n ollama-vulkan
Summary:  Vulkan runners for Ollama
Requires: ollama = %{version}-%{release}

%description -n ollama-vulkan
Bibliotecas/runners com suporte a Vulkan para o Ollama (instaladas em %{ollama_libdir}).
%endif

%if %{with rocm}
%package -n ollama-rocm
Summary:  ROCm/HIP runners for Ollama (AMD)
Requires: ollama = %{version}-%{release}

%description -n ollama-rocm
Bibliotecas/runners com suporte a ROCm/HIP para o Ollama (instaladas em %{ollama_libdir}).
Inclui, quando presente, a árvore rocBLAS/libraries embalada pelo upstream.
%endif

%prep
%setup -q -n ollama-%{version} -a 1

%check
# Confere Source1 (ollamad-main) e arquivos necessários
test -d ollamad-main
test -f ollamad-main/ollamad.service
test -f ollamad-main/ollamad.sysusers
test -f ollamad-main/ollamad.conf
# CMakePresets pode ou não existir, depende do commit
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
export CMAKE_BUILD_PARALLEL_LEVEL=%{?_smp_build_ncpus}

SRCDIR=%{_builddir}/ollama-%{version}
# Builddir totalmente externo à árvore de fontes e único por versão/arch
BUILDDIR=%{_builddir}/bld-ollama-%{version}-%{_arch}
# Saída do binário Go fora do SRCDIR
GOBINDIR=%{_builddir}/go-ollama-%{version}-%{_arch}

rm -rf "$BUILDDIR" "$GOBINDIR"
mkdir -p "$BUILDDIR" "$GOBINDIR"

# Detecção: liga apenas o backend se o diretório de fonte existir
GGML_SRC="$SRCDIR/ml/backend/ggml/ggml/src"
have_vulkan=OFF; [ -d "$GGML_SRC/ggml-vulkan" ] && have_vulkan=ON
have_hip=OFF;    { [ -d "$GGML_SRC/ggml-hip" ] || [ -d "$GGML_SRC/ggml-rocm" ]; } && have_hip=ON

# Respeita os bconds; se usuário desligar um backend, força OFF
%if %{with vulkan}
  : # mantém detecção
%else
  have_vulkan=OFF
%endif
%if %{with rocm}
  : # mantém detecção
%else
  have_hip=OFF
%endif

echo "===> GGML backends: VULKAN=$have_vulkan OPENCL=OFF HIP=$have_hip"

# Configure único conforme a documentação
cmake -S "$SRCDIR" -B "$BUILDDIR" \
  -DBUILD_SHARED_LIBS=ON \
  -DGGML_BACKEND_DL=ON \
  -DGGML_VULKAN=${have_vulkan} \
  -DGGML_OPENCL=OFF \
  -DGGML_HIP=${have_hip} \
  -DCMAKE_BUILD_TYPE=Release

# Build único
cmake --build "$BUILDDIR"

# Binário Go (uma vez só), fora do SRCDIR
( cd "$SRCDIR" && \
  if [ -f main.go ]; then \
    go build -ldflags "-s -w" -o "$GOBINDIR/ollama" . ; \
  else \
    go build -ldflags "-s - w" -o "$GOBINDIR/ollama" ./cmd/ollama ; \
  fi )

%install
rm -rf %{buildroot}

# Binário
install -Dpm0755 %{_builddir}/go-ollama-%{version}-%{_arch}/ollama %{buildroot}%{_bindir}/ollama

# Runners -> /usr/lib/ollama (apenas GPU; não copiamos libs CPU)
install -d %{buildroot}%{ollama_libdir}

# Coleta de UM ÚNICO builddir (dist preferencial; fallback lib/)
for src in \
  "%{_builddir}/bld-ollama-%{version}-%{_arch}/dist/linux-$GOARCH/lib/ollama" \
  "%{_builddir}/bld-ollama-%{version}-%{_arch}/lib/ollama" \
; do
  [ -d "$src" ] || continue
%if %{with vulkan}
  cp -a "$src"/*vulkan*.so %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
  cp -a "$src"/*vk*.so     %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
%endif
%if %{with opencl}
  # Mantido OFF por padrão; se um dia existir, habilite via --with opencl
  cp -a "$src"/*opencl*.so %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
%endif
%if %{with rocm}
  cp -a "$src"/*rocm*.so   %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
  cp -a "$src"/*hip*.so    %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
  cp -a "$src"/rocblas*/library/* %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
%endif
done

# Limpa RPATH/RUNPATH (conformidade QA Fedora)
if ls %{buildroot}%{ollama_libdir}/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{ollama_libdir}/*.so; do
    chrpath -d "$so" 2>/dev/null || true
    patchelf --remove-rpath "$so" 2>/dev/null || true
  done
fi

# systemd/sysusers/config a partir do Source1 (ollamad-main)
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

# ---------- FILES ----------
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
%{ollama_libdir}/rocblas*/library/*
%endif

%changelog
* Fri Oct 31 2025 Moacyr <you@example.org> - 0.12.7-6
- Build único conforme documentação (cmake -> build -> go build)
- Builddir externo e binário Go fora do SRCDIR
- OpenCL off por padrão; Vulkan/ROCm condicionais e autodetectados no source
- Coleta a partir de um único builddir e limpeza de RPATH/RUNPATH

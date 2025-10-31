Name:           ollama
Version:        0.12.7
Release:        5%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Paths/macros (fallbacks)
%{!?_unitdir:%global _unitdir /usr/lib/systemd/system}
%{!?_sysusersdir:%global _sysusersdir /usr/lib/sysusers.d}
# Destino único para as libs (força /usr/lib mesmo em x86_64)
%global ollama_libdir %{_prefix}/lib/ollama

# Subpacotes opcionais (habilitados por padrão)
%bcond_without vulkan
# % bcond_without opencl (não existe preset de opencl ainda no ollama)
%bcond_with opencl
%bcond_without rocm

Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

BuildRequires:  golang
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig
BuildRequires:  patchelf
BuildRequires:  chrpath
BuildRequires:  unzip
BuildRequires:  systemd-rpm-macros
BuildRequires:  ccache

# Se forem necessários headers/tooling adicionais para os backends, adicione aqui:
# (exemplos comuns)
BuildRequires:  glslc glslang
BuildRequires:  pkgconfig(vulkan)
BuildRequires:  pkgconfig(OpenCL)
BuildRequires:  rocm-devel

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%description
Ollama. Compila o binário principal e gera/liga os backends de GPU (Vulkan/OpenCL/ROCm)
em um único build. Instala serviço systemd (ollamad.service), sysusers, ambiente em
/etc/ollamad e registra %{ollama_libdir} no ldconfig.

# ---------- Subpackages ----------
%if %{with vulkan}
%package -n ollama-vulkan
Summary:  Vulkan runners for Ollama
Requires: ollama = %{version}-%{release}

%description -n ollama-vulkan
Bibliotecas/runners com suporte a Vulkan para o Ollama (instaladas em %{ollama_libdir}).
%endif

%if %{with opencl}
%package -n ollama-opencl
Summary:  OpenCL runners for Ollama
Requires: ollama = %{version}-%{release}

%description -n ollama-opencl
Bibliotecas/runners com suporte a OpenCL para o Ollama (instaladas em %{ollama_libdir}).
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

SRCDIR=%{_builddir}/ollama-%{version}
BUILDDIR=%{_builddir}/ollama-%{version}-build

# ======= UM ÚNICO CONFIGURE/BUILD HABILITANDO BACKENDS =======
# Ajuste as opções conforme o CMakeLists do commit atual do upstream.
# GGML_BACKEND_DL=ON para backends dinâmicos (.so) e os toggles de cada backend.
cmake -S "$SRCDIR" -B "$BUILDDIR" \
  -DBUILD_SHARED_LIBS=ON \
  -DGGML_BACKEND_DL=ON \
%if %{with vulkan}
  -DGGML_VULKAN=ON \
%else
  -DGGML_VULKAN=OFF \
%endif
%if %{with opencl}
  -DGGML_OPENCL=ON \
%else
  -DGGML_OPENCL=OFF \
%endif
%if %{with rocm}
  -DGGML_HIP=ON \
%else
  -DGGML_HIP=OFF \
%endif
  -DCMAKE_BUILD_TYPE=Release

cmake --build "$BUILDDIR" -j%{?_smp_build_ncpus}

# Binário Go (uma vez só)
mkdir -p %{_builddir}/ollama-%{version}
( cd "$SRCDIR" && \
  if [ -f main.go ]; then \
    go build -ldflags "-s -w" -o %{_builddir}/ollama-%{version}/ollama . ; \
  else \
    go build -ldflags "-s -w" -o %{_builddir}/ollama-%{version}/ollama ./cmd/ollama ; \
  fi )

%install
rm -rf %{buildroot}

# Binário
install -Dpm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Runners -> /usr/lib/ollama (apenas GPU; não copiamos libs CPU)
install -d %{buildroot}%{ollama_libdir}

# Coleta de UM ÚNICO builddir (dist preferencial; fallback lib/)
for src in \
  "%{_builddir}/ollama-%{version}-build/dist/linux-$GOARCH/lib/ollama" \
  "%{_builddir}/ollama-%{version}-build/lib/ollama" \
; do
  [ -d "$src" ] || continue
%if %{with vulkan}
  cp -a "$src"/*vulkan*.so %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
  cp -a "$src"/*vk*.so     %{buildroot}%{ollama_libdir}/ 2>/dev/null || true
%endif
%if %{with opencl}
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

%if %{with opencl}
%files -n ollama-opencl
%{ollama_libdir}/*opencl*.so
%endif

%if %{with rocm}
%files -n ollama-rocm
%{ollama_libdir}/*rocm*.so
%{ollama_libdir}/*hip*.so
%{ollama_libdir}/rocblas*/library/*
%endif

%changelog
* Fri Oct 31 2025 Moacyr <you@example.org> - 0.12.7-5
- Remove loop de presets; um único configure/build habilitando Vulkan/OpenCL/ROCm
- Coleta das libs a partir de um único builddir
- Mantém limpeza de RPATH/RUNPATH e destino em /usr/lib/ollama

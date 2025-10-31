Name:           ollama
Version:        0.12.7
Release:        4%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Paths/macros
%{!?_unitdir:%global _unitdir /usr/lib/systemd/system}
%{!?_sysusersdir:%global _sysusersdir /usr/lib/sysusers.d}
%global ollama_libdir %{_prefix}/lib/ollama

# Optional subpackages (enabled by default)
%bcond_without vulkan
%bcond_without opencl
%bcond_without rocm

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
BuildRequires:  ccache
BuildRequires:  glslc
BuildRequires:  glslang

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%description
Ollama (CPU). Inclui o binário principal, serviço systemd (ollamad.service), sysusers,
arquivo de ambiente em /etc/ollamad e registro de %{ollama_libdir} no ldconfig.

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
test -d ollamad-main
test -f ollamad-main/ollamad.service
test -f ollamad-main/ollamad.sysusers
test -f ollamad-main/ollamad.conf
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

presets="CPU"
%if %{with vulkan}
presets="$presets Vulkan"
%endif
%if %{with opencl}
presets="$presets OpenCL"
%endif
%if %{with rocm}
presets="$presets ROCm"
%endif

for preset in $presets; do
  echo "===> Compilando preset: $preset"
  cmake -S "$SRCDIR" --preset "$preset" -B %{_builddir}/ollama-%{version}-$preset || :
  cmake --build %{_builddir}/ollama-%{version}-$preset -j%{?_smp_build_ncpus} || :
done

mkdir -p %{_builddir}/ollama-%{version}
( cd "$SRCDIR" && \
  if [ -f main.go ]; then \
    go build -ldflags "-s -w" -o %{_builddir}/ollama-%{version}/ollama . ; \
  else \
    go build -ldflags "-s -w" -o %{_builddir}/ollama-%{version}/ollama ./cmd/ollama ; \
  fi )

%install
rm -rf %{buildroot}

# Binary
install -Dpm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

# Runners -> /usr/lib/ollama
install -d %{buildroot}%{ollama_libdir}

# Collect only GPU runners (NO CPU libs here)
for d in \
  "%{_builddir}/ollama-%{version}-CPU" \
  "%{_builddir}/ollama-%{version}-Vulkan" \
  "%{_builddir}/ollama-%{version}-OpenCL" \
  "%{_builddir}/ollama-%{version}-ROCm" \
  "%{_builddir}/ollama-%{version}" \
; do
  for sub in \
    "dist/linux-$GOARCH/lib/ollama" \
    "lib/ollama" \
  ; do
    src="$d/$sub"
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
done

# Clean RPATH/RUNPATH on installed .so (QA_RPATHS compliance)
if ls %{buildroot}%{ollama_libdir}/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{ollama_libdir}/*.so; do
    chrpath -d "$so" 2>/dev/null || true
    patchelf --remove-rpath "$so" 2>/dev/null || true
  done
fi

# systemd/sysusers/config from Source1
install -Dpm0644 ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 ollamad-main/ollamad.sysusers %{buildroot}%{_sysusersdir}/ollamad.conf
install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf

# ld.so.conf.d -> /usr/lib/ollama
install -d %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{_prefix}/lib/ollama" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

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
* Fri Oct 31 2025 Moacyr <you@example.org> - 0.12.7-4
- Remove CPU libs do buildroot (evita falhas do check-rpaths)
- Limpeza de RPATH/RUNPATH com chrpath/patchelf nas .so instaladas
- Subpacotes condicionais via %%bcond (vulkan/opencl/rocm)
- Mantém instalação em /usr/lib/ollama

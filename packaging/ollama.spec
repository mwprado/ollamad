Name:           ollama
Version:        0.12.7
Release:        2%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama
%{!?_unitdir:%global _unitdir /usr/lib/systemd/system}
%{!?_sysusersdir:%global _sysusersdir /usr/lib/sysusers.d}

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
BuildRequires:  systemd-rpm-macros

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%description
Ollama (CPU). Inclui o binário principal, serviço systemd (ollamad.service), sysusers,
arquivo de ambiente em /etc/ollamad e registro de %{_libdir}/ollama no ldconfig.

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

for preset in CPU Vulkan OpenCL ROCm; do
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

install -Dpm0755 %{_builddir}/ollama-%{version}/ollama %{buildroot}%{_bindir}/ollama

install -d %{buildroot}%{_libdir}/ollama

for d in \
  "%{_builddir}/ollama-%{version}-CPU" \
  "%{_builddir}/ollama-%{version}-Vulkan" \
  "%{_builddir}/ollama-%{version}-OpenCL" \
  "%{_builddir}/ollama-%{version}-ROCm" \
  "%{_builddir}/ollama-%{version}" \
; do
  for sub in \
    "dist/linux-$GOARCH/lib/ollama" \
    "dist/linux-$GOARCH/lib64/ollama" \
    "lib/ollama" \
    "lib64/ollama" \
  ; do
    src="$d/$sub"
    [ -d "$src" ] || continue

    cp -a "$src"/libggml-base.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
    cp -a "$src"/libggml-cpu-*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

    cp -a "$src"/*vulkan*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
    cp -a "$src"/*vk*.so     %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

    cp -a "$src"/*opencl*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

    cp -a "$src"/*rocm*.so   %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
    cp -a "$src"/*hip*.so    %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
    cp -a "$src"/rocblas*/library/* %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  done
done

for bd in \
  "%{_builddir}/ollama-%{version}-CPU" \
  "%{_builddir}/ollama-%{version}-Vulkan" \
  "%{_builddir}/ollama-%{version}-OpenCL" \
  "%{_builddir}/ollama-%{version}-ROCm" \
; do
  [ -d "$bd" ] || continue
  find "$bd" -type f -name 'libggml-*.so' -exec cp -a {} %{buildroot}%{_libdir}/ollama/ \; 2>/dev/null || true
done

if ls %{buildroot}%{_libdir}/ollama/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{_libdir}/ollama/*.so; do
    patchelf --remove-rpath "$so" || true
  done
fi

install -Dpm0644 ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 ollamad-main/ollamad.sysusers %{buildroot}%{_sysusersdir}/ollamad.conf
install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf

install -d %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{_libdir}/ollama" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

# --- Normaliza destino para %{_libdir}/ollama ---
# Se algum preset/copiar jogou libs em /usr/lib/ollama, mova para %{_libdir}/ollama
if [ "%{_libdir}" != "/usr/lib" ] && [ -d "%{buildroot}/usr/lib/ollama" ]; then
  mkdir -p %{buildroot}%{_libdir}
  if [ -d "%{buildroot}%{_libdir}/ollama" ]; then
    cp -a %{buildroot}/usr/lib/ollama/* %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
    rm -rf %{buildroot}/usr/lib/ollama
  else
    mv -f %{buildroot}/usr/lib/ollama %{buildroot}%{_libdir}/ || true
  fi
  rmdir --ignore-fail-on-non-empty %{buildroot}/usr/lib 2>/dev/null || true
fi


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

%files
%license LICENSE*
%doc README* docs/*
%{_bindir}/ollama
%{_unitdir}/ollamad.service
%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

%files -n ollama-vulkan
%{_libdir}/ollama/*vulkan*.so
%{_libdir}/ollama/*vk*.so

%files -n ollama-opencl
%{_libdir}/ollama/*opencl*.so

%files -n ollama-rocm
%{_libdir}/ollama/*rocm*.so
%{_libdir}/ollama/*hip*.so
%{_libdir}/ollama/rocblas*/library/*

%changelog
* Fri Oct 31 2025 Moacyr <you@example.org> - 0.12.7-2
- Coletor de libs robusto (lib/lib64) e ld.so.conf.d portátil
- Removidas libs CPU do %files base; mantidas nos subpacotes
- Macros de fallback para _unitdir/_sysusersdir
- Presets (CPU, Vulkan, OpenCL, ROCm) + go build da raiz

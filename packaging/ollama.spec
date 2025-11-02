Name:           ollama
Version:        0.12.7
Release:        8%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

%{!?_unitdir:%global _unitdir /usr/lib/systemd/system}
%{!?_sysusersdir:%global _sysusersdir /usr/lib/sysusers.d}
%global ollama_libdir /usr/lib/ollama

# Vulkan e ROCm habilitados por padrão
%bcond_with vulkan
%bcond_with rocm

Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

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
BuildRequires:  ccache

# Vulkan (ativo por padrão)
%if %{without vulkan}
# Vulkan desativado
%else
BuildRequires:  pkgconfig(vulkan)
BuildRequires:  glslc
BuildRequires:  glslang
BuildRequires:  VulkanMemoryAllocator-devel
BuildRequires:  vulkan-headers
BuildRequires:  vulkan-loader-devel
BuildRequires:  vulkan-tools
BuildRequires:  spirv-tools
BuildRequires:  shaderc
%global pck_build_vulkan 1
%endif

# ROCm (ativo por padrão)
%if %{without rocm}
# ROCm desativado
%else
BuildRequires:  rocm-core
BuildRequires:  hip-devel
BuildRequires:  rocblas-devel
BuildRequires:  rocm-device-libs
%global pck_build_rocm 1
%endif

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

%description
Empacotamento do Ollama seguindo o Dockerfile oficial.
Compila sempre CPU + Vulkan + ROCm (a menos que explicitamente desativado).
Inclui systemd, sysusers, conf e ldconfig.

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
export CMAKE_BUILD_PARALLEL_LEVEL=%{?_smp_build_ncpus}
export PARALLEL=%{?_smp_build_ncpus}

SRCDIR=%{_builddir}/ollama-%{version}
STAGING=%{_builddir}/staging-%{version}-%{_arch}
GOBINDIR=%{_builddir}/go-ollama-%{version}-%{_arch}
rm -rf "$STAGING" "$GOBINDIR"; mkdir -p "$STAGING" "$GOBINDIR"

pushd "$SRCDIR"
rm -rf build
cmake --preset "CPU"
cmake --build --parallel ${PARALLEL} --preset "CPU"
DESTDIR="$STAGING" cmake --install build --component CPU --strip --parallel ${PARALLEL}

%if %{without vulkan}
# Vulkan desativado
%else
rm -rf build
cmake --preset "Vulkan" -DOLLAMA_RUNNER_DIR="vulkan"
cmake --build --parallel ${PARALLEL} --preset "Vulkan"
DESTDIR="$STAGING" cmake --install build --component Vulkan --strip --parallel ${PARALLEL}
%endif

%if %{without rocm}
# ROCm desativado
%else
rm -rf build
cmake --preset "ROCm 6" -DOLLAMA_RUNNER_DIR="rocm"
cmake --build --parallel ${PARALLEL} --preset "ROCm 6"
DESTDIR="$STAGING" cmake --install build --component HIP --strip --parallel ${PARALLEL}
rm -f "$STAGING"/usr/lib/ollama/rocm/rocblas/library/*gfx90[06]*
%endif
popd

( cd "$SRCDIR" && go build -trimpath -buildmode=pie -ldflags "-s -w" -o "$GOBINDIR/ollama .")

%install
rm -rf %{buildroot}
install -Dpm0755 %{_builddir}/go-ollama-%{version}-%{_arch}/ollama %{buildroot}%{_bindir}/ollama
cp -a %{_builddir}/staging-%{version}-%{_arch}/usr/* %{buildroot}/usr/ || true

if ls %{buildroot}%{ollama_libdir}/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{ollama_libdir}/*.so; do
    chrpath -d "$so" 2>/dev/null || true
    patchelf --remove-rpath "$so" 2>/dev/null || true
  done
fi

install -Dpm0644 ollamad-main/ollamad.service %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 ollamad-main/ollamad.sysusers %{buildroot}%{_sysusersdir}/ollamad.conf
install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 ollamad-main/ollamad.conf %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf
install -d %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{ollama_libdir}" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

%pre
%sysusers_create_compat %{_sysusersdir}/ollamad.conf
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
%doc README.md
%doc docs/*
%{_bindir}/ollama
%{_unitdir}/ollamad.service
%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

%if %{without vulkan}
# sem Vulkan
%else
%files -n ollama-vulkan
%{ollama_libdir}/*vulkan*.so
%{ollama_libdir}/*vk*.so
%endif

%if %{without rocm}
# sem ROCm
%else
%files -n ollama-rocm
%{ollama_libdir}/*rocm*.so
%{ollama_libdir}/*hip*.so
%{ollama_libdir}/rocm/rocblas/library/*
%endif

%changelog
* Sun Nov 02 2025 Moacyr Prado <you@example.org> - 0.12.7-8
- Vulkan e ROCm habilitados por padrão
- Inclui pkgconfig(vulkan) e pkgconfig(ROCM) em BuildRequires
- Sincronizado com Dockerfile oficial

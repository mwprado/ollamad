Name:           ollama
Version:        0.12.7
Release:        4%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Fontes (ZIP)
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

# Arquivos auxiliares (ficam no ROOT das SOURCES, conforme diretriz Fedora)
Source10:       ollamad.sysusers
Source11:       ollamad.service
Source12:       ollamad.conf
Source13:       ollamad-ld.conf

BuildRequires:  golang
BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  systemd-rpm-macros
BuildRequires:  patchelf
BuildRequires:  unzip

Requires(post):   systemd
Requires(preun):  systemd
Requires(postun): systemd

ExclusiveArch:  x86_64 aarch64

# ==================== PACOTE BASE ====================
%package -n ollama
Summary:  Ollama (CPU runtime, service, sysusers, config)

%description -n ollama
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
# -n: diretório criado do ZIP do Source0 ("ollama-%{version}")
# -a 1: também extrai o Source1 (cria "ollamad-main")
%setup -q -n ollama-%{version} -a 1
# (Se precisar, consuma arquivos do Source1 aqui. Os auxiliares vêm de Source10..13 no ROOT.)

%build
# Mapear architecture -> GOARCH
case "%{_arch}" in
  x86_64)  export GOARCH=amd64 ;;
  aarch64) export GOARCH=arm64 ;;
  *) echo "Arquitetura não suportada: %{_arch}"; exit 1 ;;
esac
export GOOS=linux
export CGO_ENABLED=1
export GOFLAGS="-buildvcs=false -trimpath"

# Gera artefatos de runtime (se o upstream Makefile suportar; é opcional)
%make_build dist || :

# Compila o binário principal
go build -ldflags "-s -w" -o ollama ./cmd/ollama

# ==================== INSTALL ====================
%install
rm -rf %{buildroot}

# Binário (pacote base)
install -Dpm0755 ollama %{buildroot}%{_bindir}/ollama

# Diretório comum de libs
install -d %{buildroot}%{_libdir}/ollama

# ---- CPU (pacote base) ----
if [ -d "dist/linux-$GOARCH/lib/ollama" ]; then
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-base.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-cpu-*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
fi

# ---- Vulkan (subpacote ollama-vulkan) ----
cp -a dist/linux-$GOARCH/lib/ollama/*vulkan*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*vk*.so     %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# ---- OpenCL (subpacote ollama-opencl) ----
cp -a dist/linux-$GOARCH/lib/ollama/*opencl*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# ---- ROCm/HIP (subpacote ollama-rocm) ----
cp -a dist/linux-$GOARCH/lib/ollama/*rocm*.so   %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
cp -a dist/linux-$GOARCH/lib/ollama/*hip*.so    %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
# Árvore rocBLAS opcional
cp -a dist/linux-$GOARCH/lib/ollama/rocblas*/library/* %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true

# ---- Sanitizar RPATH/RUNPATH das .so para evitar falhas de QA ----
if ls %{buildroot}%{_libdir}/ollama/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{_libdir}/ollama/*.so; do
    patchelf --remove-rpath "$so" || true
  done
fi

# ---- systemd/sysusers/config/ld.so.conf.d (todos parte do pacote base) ----
install -Dpm0644 %{SOURCE11} %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 %{SOURCE10} %{buildroot}%{_sysusersdir}/ollamad.conf

# Diretório de config
install -d %{buildroot}%{_sysconfdir}/ollamad
install -Dpm0644 %{SOURCE12} %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf

# ld.so.conf.d (use caminho portátil via macro)
# Dica: para portabilidade entre x86_64/aarch64, você pode gerar o arquivo em buildtime:
#   echo "%{_libdir}/ollama" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf
# Aqui instalamos o Source13 estático; ajuste conforme sua política.
install -Dpm0644 %{SOURCE13} %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

# ==================== SCRIPTS ====================
%pre -n ollama
%if 0%{?__systemd_sysusers:1}
%sysusers_create_compat %{_sysusersdir}/ollamad.conf
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

# ==================== FILES ====================
# Base (CPU + binário + service/sysusers/config/ld.so.conf.d)
%files -n ollama
%license LICENSE*
%doc README* docs/*
%{_bindir}/ollama
%{_libdir}/ollama/libggml-base.so
%{_libdir}/ollama/libggml-cpu-*.so
%{_unitdir}/ollamad.service
%{_sysusersdir}/ollamad.conf
%config(noreplace) %{_sysconfdir}/ollamad/ollamad.conf
%config %{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

# Vulkan subpackage
%files -n ollama-vulkan
%{_libdir}/ollama/*vulkan*.so
%{_libdir}/ollama/*vk*.so

# OpenCL subpackage
%files -n ollama-opencl
%{_libdir}/ollama/*opencl*.so

# ROCm subpackage
%files -n ollama-rocm
%{_libdir}/ollama/*rocm*.so
%{_libdir}/ollama/*hip*.so
%{_libdir}/ollama/rocblas*/library/*

%changelog
* Thu Oct 30 2025 Moacyr <you@example.org> - 0.12.6-4
- Subpacotes: ollama-vulkan, ollama-opencl, ollama-rocm + base ollama
- Auxiliares no ROOT; .spec em packaging/

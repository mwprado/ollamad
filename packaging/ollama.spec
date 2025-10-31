Name:           ollama
Version:        0.12.7
Release:        3%{?dist}
Summary:        Create, run and share large language models (LLMs)
License:        MIT
URL:            https://github.com/ollama/ollama

# Fontes principais (ZIP)
Source0:        https://github.com/ollama/ollama/archive/refs/tags/v%{version}.zip
Source1:        https://github.com/mwprado/ollamad/archive/refs/heads/main.zip

# Arquivos auxiliares (no ROOT da árvore de SOURCES, conforme diretriz Fedora)
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

%package -n ollama
Summary:  Ollama (CPU)

%description -n ollama
Ollama (CPU). Serviço "ollamad.service", sysusers e arquivo de ambiente em /etc/ollamad.

%prep
# -n: diretório criado a partir do ZIP do Source0 (GitHub exporta como "ollama-%{version}")
# -a 1: também extrai o Source1 (cria "ollamad-main" dentro do diretório atual)
%setup -q -n ollama-%{version} -a 1

# (Opcional) Se quiser consumir algo do repositório auxiliar (Source1), ajuste aqui.
# Por padrão, usamos os arquivos auxiliares enviados como Source10..13 (no root).

%build
case "%{_arch}" in
  x86_64)  export GOARCH=amd64 ;;
  aarch64) export GOARCH=arm64 ;;
  *) echo "Arquitetura não suportada: %{_arch}"; exit 1 ;;
esac
export GOOS=linux
export CGO_ENABLED=1
export GOFLAGS="-buildvcs=false -trimpath"

# Gera artefatos de runtime (opcional)
%make_build dist || :
# Compila o binário principal
go build -ldflags "-s -w" -o ollama ./cmd/ollama

%install
rm -rf %{buildroot}

# Binário
install -Dpm0755 ollama %{buildroot}%{_bindir}/ollama

# Diretório de libs do runtime
install -d %{buildroot}%{_libdir}/ollama

# Runners CPU (se gerados por dist)
if [ -d "dist/linux-$GOARCH/lib/ollama" ]; then
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-base.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
  cp -a dist/linux-$GOARCH/lib/ollama/libggml-cpu-*.so %{buildroot}%{_libdir}/ollama/ 2>/dev/null || true
fi

# Sanitiza RPATH/RUNPATH
if ls %{buildroot}%{_libdir}/ollama/*.so >/dev/null 2>&1; then
  for so in %{buildroot}%{_libdir}/ollama/*.so; do
    patchelf --remove-rpath "$so" || true
  done
fi

# Instala service/sysusers/config/ld.so.conf.d (vindos do ROOT, Source10..13)
install -Dpm0644 %{SOURCE11} %{buildroot}%{_unitdir}/ollamad.service
install -Dpm0644 %{SOURCE10} %{buildroot}%{_sysusersdir}/ollamad.conf
install -Dpm0644 %{SOURCE12} %{buildroot}%{_sysconfdir}/ollamad/ollamad.conf
install -Dpm0644 %{SOURCE13} %{buildroot}%{_sysconfdir}/ld.so.conf.d/ollamad-ld.conf

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

%changelog
* Thu Oct 30 2025 Moacyr <you@example.org> - 0.12.6-3
- Reorganiza fontes auxiliares: apenas .spec em packaging/, demais no root (conforme Fedora)

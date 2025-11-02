# Requisitos de build básicos
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

# Vulkan (habilitado por padrão, desativa com --without vulkan)
%if %{without vulkan}
# Vulkan desativado explicitamente
%else
BuildRequires:  glslc
BuildRequires:  glslang
BuildRequires:  spirv-tools
BuildRequires:  shaderc
BuildRequires:  pkgconfig(Vulkan)
%global pck_build_vulkan 1
%endif

# ROCm (habilitado por padrão, desativa com --without rocm)
%if %{without rocm}
# ROCm desativado explicitamente
%else
BuildRequires:  rocm-core
BuildRequires:  hip-devel
BuildRequires:  rocblas-devel
BuildRequires:  rocm-device-libs
BuildRequires:  pkgconfig(hip)
%global pck_build_rocm 1
%endif

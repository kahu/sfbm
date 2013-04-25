#
# spec file for package python3-xdg
#
# Copyright (c) 2013 Ka Hu <kahu2000@gmail.com>

Name:           sfbm
Version:        0.7.2
Release:        0
License:        GPL-3.0
Summary:        Menu-based file browser in the system tray
Url:            https://github.com/kahu/sfbm
Group:          Productivity/File utilities
Source:         %{name}-%{version}.tar.gz
BuildRequires:  fdupes
BuildRequires:  python3-devel
BuildRequires:  python3-distribute
Requires:       python3-qt4
Requires:       python3-xdg
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

%description
SFBM is a simple file browser in the form of a menu.

%prep
%setup -q

%build
python3 setup.py build

%install
python3 setup.py install -O1 --skip-build --root=%{buildroot} --prefix="%{_prefix}"
%fdupes %{buildroot}/%{python3_sitelib}

%files
%defattr(-, root, root)
%{_bindir}/stupid-file-browser-menu
%{python3_sitelib}/*
%{_datadir}/applications/%{name}.desktop
%{_datadir}/pixmaps/%{name}.svg

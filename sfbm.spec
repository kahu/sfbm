#
# spec file for package python3-xdg
#
# Copyright (c) 2013 Ka Hu <kahu2000@gmail.com>

Name:             sfbm
Summary:          Menu-based file browser in the sytem tray.
License:          GPL-3.0
Group:            Productivity/File utilities
Version:          0.7
Release:          0
Url:              https://github.com/kahu/sfbm
Source:           %{name}-%{version}.tar.gz
BuildRequires:    python3-devel
BuildRequires:    python3-distribute
BuildRoot:        %{_tmppath}/%{name}-%{version}-build
Requires:         python3-xdg
Requires:         python3-qt4

%description
SFBM is a simple file browser in the form of a menu.

%prep
%setup -q -n %{name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install -O1 --skip-build --root="%{buildroot}" --prefix="%{_prefix}"
%fdupes %{buildroot}/%{python3_sitelib}

%files
%defattr(-, root, root)
%{_bindir}/stupid-file-browser-menu
%{python3_sitelib}/*
%{_datadir}/applications/%{name}.desktop
%{_datadir}/pixmaps/%{name}.svg

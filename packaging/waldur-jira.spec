Name: waldur-jira
Summary: JIRA plugin for Waldur
Group: Development/Libraries
Version: 0.6.0
Release: 1.el7
License: MIT
Url: http://waldur.com
Source0: %{name}-%{version}.tar.gz

Requires: waldur-core >= 0.151.3
Requires: python-jira >= 1.0.4

BuildArch: noarch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

BuildRequires: python-setuptools

%description
Plugin for interaction with and management of Atlassian JIRA.

%prep
%setup -q -n %{name}-%{version}

%build
python setup.py build

%install
rm -rf %{buildroot}
python setup.py install --single-version-externally-managed -O1 --root=%{buildroot} --record=INSTALLED_FILES

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%defattr(-,root,root)

%changelog
* Sat Feb 3 2018 Jenkins <jenkins@opennodecloud.com> - 0.6.0-1.el7
- New upstream release

* Fri Dec 22 2017 Victor Mireyev <victor@opennodecloud.com> - 0.5.2-1.el7
- Initial release.

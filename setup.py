#!/usr/bin/env python
import sys
from setuptools import setup, find_packages


dev_requires = [
    'Sphinx==1.2.2',
]

install_requires = [
    'nodeconductor>0.92.0',
    'jira>=1.0.4',
]


# RPM installation does not need oslo, cliff and stevedore libs -
# they are required only for installation with setuptools
try:
    action = sys.argv[1]
except IndexError:
    pass
else:
    if action in ['develop', 'install', 'test', 'bdist_egg']:
        install_requires += [
            'cliff==1.7.0',
            'oslo.config==1.4.0',
            'oslo.i18n==1.0.0',
            'oslo.utils==1.0.0',
            'stevedore==1.0.0',
        ]


setup(
    name='nodeconductor-jira',
    version='0.2.1',
    author='OpenNode Team',
    author_email='info@opennodecloud.com',
    url='http://nodeconductor.com',
    description='Plugin for interaction and management of Atlassian JIRA',
    long_description=open('README.rst').read(),
    package_dir={'': 'src'},
    packages=find_packages('src', exclude=['*.tests', '*.tests.*', 'tests.*', 'tests']),
    dependency_links=['git+https://github.com/pycontribs/jira@e829da6980980e0291c5787442524edc822a94fb#egg=jira-1.0.4'],
    install_requires=install_requires,
    zip_safe=False,
    extras_require={
        'dev': dev_requires,
    },
    entry_points={
        'nodeconductor_extensions': (
            'nodeconductor_jira = nodeconductor_jira.extension:JiraExtension',
        ),
    },
    include_package_data=True,
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Apache Software License',
    ],
)

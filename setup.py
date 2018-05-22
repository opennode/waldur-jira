#!/usr/bin/env python
from setuptools import setup, find_packages

test_requires = [
    'ddt>=1.0.0'
]

install_requires = [
    'waldur-core>=0.151.3',
    'jira>=1.0.4',
]


setup(
    name='waldur-jira',
    version='0.8.1',
    author='OpenNode Team',
    author_email='info@opennodecloud.com',
    url='http://waldur.com',
    description='Plugin for interaction and management of Atlassian JIRA',
    license='MIT',
    long_description=open('README.rst').read(),
    package_dir={'': 'src'},
    packages=find_packages('src', exclude=['*.tests', '*.tests.*', 'tests.*', 'tests']),
    install_requires=install_requires,
    zip_safe=False,
    extras_require={
        'test': test_requires,
    },
    entry_points={
        'waldur_extensions': (
            'waldur_jira = waldur_jira.extension:JiraExtension',
        ),
    },
    include_package_data=True,
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
)

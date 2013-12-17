from setuptools import setup, find_packages
import os

version = '2.2.1dev'

setup(name='silva.searchandreplace',
      version=version,
      description="Search in all Silva documents and replace information in Silva 2.x",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Framework :: Zope2",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: BSD License",
        ],
      keywords='silva silvadocument search replace service',
      author='Guido Wesdorp',
      author_email='info@infrae.com',
      url='https://github.com/silvacms/silva.searchandreplace',
      license='BSD',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['silva'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'setuptools',
        'lxml',
        'silva.core.interfaces',
        'silva.core.services',
        'silva.core.conf',
        'Products.Silva >= 2.2dev',
        ],
      )

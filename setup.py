from setuptools import setup

setup(
    name='spc',
    version='0.6',
    description='Python-based SPC charting.  Developed by the PDEV team at Caelux.',
    url='https://github.com/diegosilvacaelux/spc',
    author='Diego Tapia Silva',
    author_email='diego.silva@caelux.com',
    license='Apache 2.0 (http://www.apache.org/licenses/LICENSE-2.0)',
    install_requires=[ #Many of the packages are not in PyPi, so assume the user knows how to install them!
        # 'numpy',
        # 'pandas',
    ],
    zip_safe=False
)
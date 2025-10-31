from setuptools import setup, find_packages

setup(
    name='spc',
    version='0.6',
    description='Python-based SPC charting. Developed by the PDEV team at Caelux.',
    url='https://github.com/diegosilvacaelux/spc',
    author='Diego Tapia Silva',
    author_email='diego.silva@caelux.com',
    license='Apache 2.0 (http://www.apache.org/licenses/LICENSE-2.0)',
    packages=find_packages(),
    install_requires=[
        # e.g., 'numpy', 'pandas',
    ],
    entry_points={
        'console_scripts': [
            'spc = spc.spc_process:main',
        ],
    },
    zip_safe=False,
)

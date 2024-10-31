from skbuild import setup
from setuptools import find_packages


setup(
    name="uza",
    version="0.0.1",
    packages=find_packages(),
    package_data={"uza": ["*.so", "*.so", "*.dll"], "vm": ["*.so", "*.so", "*.dll"]},
    include_package_data=True,
    cmake_install_dir="vm",
    cmake_args=["-DCMAKE_BUILD_TYPE=Release"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "uza = uza.cli:main",
        ]
    },
    python_requires=">=3.10",
    install_requires=[],
)

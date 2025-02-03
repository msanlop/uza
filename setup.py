from skbuild import setup
from setuptools import find_packages

setup(
    name="uza",
    version="0.0.1",
    packages=["uzac", "vm"],
    package_data={"vm": ["*.so", "*.so", "*.dll"]},
    include_package_data=True,
    cmake_args=["-DCMAKE_BUILD_TYPE=Release"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "uza = uzac.cli:main",
        ]
    },
    python_requires=">=3.10",
    install_requires=[],
)

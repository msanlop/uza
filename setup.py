from skbuild import setup
from setuptools import find_packages

# print(packages)

setup(
    name="uza",
    version="0.0.1",
    packages=["uza", "vm"],
    package_dir={
        "uza": "src/uza",
        "vm": "src/vm",
    },
    package_data={"uza": ["libs/*.so", "libs/*.so", "libs/*.dll", "libs/lib*"]},
    include_package_data=True,
    # packages=["uza", "vm"],
    # cmake_install_dir="src/uza",
    cmake_args=["-DCMAKE_BUILD_TYPE=Release"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "uza = uza.main:main",
        ]
    },
    python_requires=">=3.10",
    install_requires=[],
)

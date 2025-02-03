from skbuild import setup
import setuptools_scm

setup(
    name="uza",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
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

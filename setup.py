from setuptools import find_packages, setup

setup(
    name="legallink-fastapi",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
    ],
)

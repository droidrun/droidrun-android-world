from setuptools import setup, find_packages
import os


def resolve_local_package(pkg):
    abs_pkg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), pkg))
    pkg_file_url = f"file://{abs_pkg_path}"
    return f"{pkg} @ {pkg_file_url}"


setup(
    name="droidrun-android-world",
    version="0.1.0",
    description="Droidrun Android World Benchmark Runner",
    author="Timo Beckmann",
    author_email="timo@droidrun.ai",
    python_requires=">=3.11",
    packages=find_packages(include=["eval", "eval.*"]),
    install_requires=[
        resolve_local_package("droidrun"),
        resolve_local_package("android_world"),
    ],
    include_package_data=True,
    classifiers=[],
    entry_points={
        "console_scripts": {
            "droidrun-android-world=eval.cli:cli",
        },
    },
)

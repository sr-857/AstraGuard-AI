from setuptools import find_packages, setup

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="astraguard-ai",
    version="1.0.0",
    packages=find_packages(exclude=["tests*"]),
    install_requires=requirements,
    python_requires=">=3.9",
    # Additional metadata from pyproject.toml
    author="Subhajit Roy",
    author_email="your.email@example.com",
    description="Autonomous Fault Detection & Recovery System for CubeSats",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/sr-857/AstraGuard-AI",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)

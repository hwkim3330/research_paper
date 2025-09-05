#!/usr/bin/env python3
"""
CBS 1 Gigabit Ethernet Implementation
Setup script for PyPI distribution
"""

from setuptools import setup, find_packages
import os

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Version info
VERSION = "2.0.0"

setup(
    name="cbs-1gbe",
    version=VERSION,
    author="CBS Research Team",
    author_email="cbs-research@example.com",
    description="IEEE 802.1Qav Credit-Based Shaper implementation for 1 Gigabit Ethernet",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hwkim3330/research_paper",
    project_urls={
        "Bug Reports": "https://github.com/hwkim3330/research_paper/issues",
        "Source": "https://github.com/hwkim3330/research_paper",
        "Documentation": "https://hwkim3330.github.io/research_paper",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Telecommunications Industry",
        "Topic :: System :: Networking",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Natural Language :: English",
        "Natural Language :: Korean",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "flake8>=6.0.0",
            "mypy>=1.5.1",
            "pre-commit>=3.3.0",
        ],
        "ml": [
            "torch>=2.0.1",
            "tensorflow>=2.13.0",
            "xgboost>=1.7.6",
        ],
        "hardware": [
            "scapy>=2.5.0",
            "paramiko>=3.2.0",
            "pyserial>=3.5",
        ],
        "docs": [
            "sphinx>=7.1.2",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cbs-calculator=src.cbs_calculator:main",
            "cbs-simulator=src.network_simulator:main",
            "cbs-optimizer=src.ml_optimizer:main",
            "cbs-dashboard=src.dashboard:main",
            "cbs-benchmark=src.performance_benchmark:main",
            "cbs-test=run_tests:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.json", "*.md", "*.txt"],
        "src": ["*.yaml", "*.json"],
        "config": ["*.yaml", "*.json"],
        "data": ["*.json"],
    },
    keywords=[
        "TSN", "Time-Sensitive Networking", "IEEE 802.1Qav", 
        "Credit-Based Shaper", "Ethernet", "QoS", 
        "Automotive", "Industrial Automation", "Video Streaming",
        "Network Simulation", "Machine Learning", "1 Gigabit"
    ],
    zip_safe=False,
)
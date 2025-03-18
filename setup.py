"""
MedCrawler package setup.
"""
import re
from setuptools import setup, find_packages

# Read version from package __init__.py
with open('crawlers/__init__.py', 'r') as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    version = version_match.group(1) if version_match else '0.0.1'

# Read long description from README
with open('README.md', 'r') as f:
    long_description = f.read()

# Read requirements from requirements.txt
with open('requirements.txt', 'r') as f:
    requirements = [line.strip() for line in f if line.strip()]

setup(
    name="medcrawler",
    version=version,
    author="MedCrawler Team",
    author_email="example@example.com",
    description="Asynchronous crawlers for medical literature databases",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/MedCrawler",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Healthcare Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'medcrawler=crawlers.demo:main',
        ],
    },
)
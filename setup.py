"""Setup configuration for GT8004 Python SDK."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gt8004-sdk",
    version="0.2.0",
    author="GT8004 Team",
    author_email="support@gt8004.com",
    description="Python SDK for GT8004 agent analytics and observability",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vataops/gt8004-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "fastapi": ["fastapi>=0.100.0", "starlette>=0.27.0"],
        "mcp": ["fastmcp>=2.0"],
        "all": ["fastapi>=0.100.0", "starlette>=0.27.0", "fastmcp>=2.0"],
        "dev": ["pytest>=7.0.0", "pytest-asyncio>=0.21.0"],
    },
)

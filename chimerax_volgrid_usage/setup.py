from setuptools import setup, find_packages
import os

# Read requirements from the volgrids environment
requirements_path = os.path.join("src", "volgrids-main", "environment", "requirements.txt")
install_requires = []
if os.path.exists(requirements_path):
    with open(requirements_path, 'r') as f:
        install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="ChimeraX-SmifferTool",
    version="1.0",
    description="Volumetric grid analysis tool for ChimeraX with Smiffer and APBS integration",
    author="Louis Meuret",
    author_email="contact@example.com",
    url="https://github.com/DiegoBarMor/smiffer-plugins",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "": ["*.xml", "*.ini", "*.chem", "*.md", "*.txt", "*.yml", "*.sh"],
        "volgrids": ["config.ini"],
        "volgrids.smiffer.tables": ["*.chem"],
    },
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.8",
    entry_points={
        "chimerax.bundles": [
            "chimerax.smiffertool = chimerax.smiffertool:bundle_api",
        ],
    },
)

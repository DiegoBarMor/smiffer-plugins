from setuptools import setup

setup(
    name="ChimeraX-OrientationTool",
    version="1.0",
    description="Orientation management tool for ChimeraX",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://example.com",
    packages=["chimerax.orientationtool"],
    package_dir={"chimerax.orientationtool": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.6",
)

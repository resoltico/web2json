from setuptools import setup, find_packages

# Import VERSION from config.py
try:
    from web2json.config import VERSION
except ImportError:
    # Default version if import fails during initial setup
    VERSION = "1.0.0"

setup(
    name="web2json",
    version=VERSION,
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.13.3",
        "requests>=2.32.3",
    ],
    entry_points={
        "console_scripts": [
            "web2json=web2json.cli:main",
        ],
    },
    python_requires=">=3.6",  # Based on f-strings usage in the code
    author="Ervins Strauhmanis",
    description="Web page to structured JSON converter",
    long_description="""
    web2json - Web page to structured JSON converter
    
    This tool converts web pages into structured JSON format for easier
    data processing and analysis. It extracts headings, paragraphs, lists,
    and other elements into a consistent structure.
    
    For Windows users: After installation, run the windows_setup.py script
    to create helper scripts for your environment.
    """,
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Text Processing :: Markup :: HTML",
    ],
    keywords="web scraping, json conversion, html parser",
    project_urls={
        "Documentation": "https://github.com/resoltico/web2json",
        "Source": "https://github.com/resoltico/web2json",
        "Tracker": "https://github.com/resoltico/web2json/issues",
    },
)

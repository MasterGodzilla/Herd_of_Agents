from setuptools import setup, find_packages

setup(
    name="herd_agents",
    version="0.1.0",
    description="A multi-agent system framework for autonomous agents",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "openai",
        "google-genai", 
        "anthropic",
        "requests",
        "tenacity"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 
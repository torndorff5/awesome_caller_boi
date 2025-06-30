from setuptools import setup, find_packages

setup(
    name="awesome_caller_boi",               # your package name
    version="0.2.4",
    author="Orndorff Automation",
    author_email="torndorff5@gmail.com",
    description="A FastAPI router + Twilio⇆OpenAI realtime streaming helper",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/torndorff5/awesome_caller_boi",  # optional
    packages=find_packages(),                # finds the inner call_logic folder
    python_requires=">=3.8",                 # or your minimum version
    install_requires=[
        "fastapi>=0.70",
        "uvicorn>=0.15",
        "websockets>=10.0",
        "twilio>=7.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
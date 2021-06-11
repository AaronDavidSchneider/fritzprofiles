import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="fritzprofiles",
    version="0.6.1",
    author="Aaron David Schneider",
    author_email="aaron.david.schneider@gmail.com",
    description="A tool to switch the online time of profiles in the AVM Fritz!Box",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AaronDavidSchneider/fritzprofiles",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
   'requests',
   'lxml'
    ],
    scripts=["bin/fritzprofiles"]
)

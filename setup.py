#!/usr/bin/python3

from distutils.core import setup

setup(name="sfbm",
      author="Ka Hu",
      author_email="kahu2000@gmail.com",
      license="GPLv3",
      version="0.6",
      packages=["sfbm"],
      package_data={"sfbm": ["data/*"]},
      scripts=["stupid-file-browser-menu"],
      data_files=[("share/applications", ["sfbm.desktop"]),
                  ("share/pixmaps", ["sfbm.svg"])],
      )

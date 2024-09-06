# DKSR City Mission - Prague 2024

From September 16th to 20th, Prague will host the first-ever DKSR City Mission.

In this repository, you will find the relevant analysis and source code used for the different use cases.

For a detailed description of each use case and its respective analysis, refer to the corresponding `README.md`.

## For Developers

To ensure reproducibility and portability of the code, Docker is recommended. The `Dockerfile` in the root directory uses multi-stage builds to accommodate the three use cases. Specify which use case you are working on using the `--target` argument (also to be updated in the `devcontainer.json` if you are using VSCode).

The `requirements.txt` in the root directory contains packages that we consider essential for a data science project. You can add use case-specific packages in the respective folders.

Additionally, the `.gitignore` is customized for each use case.

Happy coding! :)

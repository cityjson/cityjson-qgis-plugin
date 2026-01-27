# Contributing to CityJsonLoader (QGIS Plugin)

Thank you for your interest in contributing to CityJsonLoader! Contributions are welcome and much appreciated.

## How to Contribute

- **Pull Requests:**
  - Please submit your changes as a Pull Request (PR) against the `development` branch.
  - Make sure your PR clearly describes the changes and the motivation behind them.
  - We prefer small PR that are focused on improving one things rather than huge PR with changes in multiple files. 

- **Code Style & Formatting:**
  - Ensure your code follows the existing style and conventions of the project.
  - We use [ruff](https://docs.astral.sh/ruff/) for linting/formatting and [pre-commit](https://pre-commit.com/) for automated code checks.
  - Before submitting your PR, make sure to:
    1. Create and activate a virtual environment for development (recommended):
       ```sh
       python -m venv .venv
       source .venv/bin/activate  # On Windows use: venv\Scripts\activate
       ```
    2. Install ruff and pre-commit:
       ```sh
       pip install ruff pre-commit
       ```
    3. Install the pre-commit hooks:
       ```sh
       pre-commit install
       ```
    4. (Optional) Run all hooks on all files:
       ```sh
       pre-commit run --all-files
       ```
  - This will help ensure your code passes all style and quality checks automatically before each commit.

- **Testing:**
  - Run all tests before submitting your PR to ensure nothing is broken.
  - Add new tests for any new features or bug fixes when possible.

- **Reporting Issues:**
  - If you find a bug or have a feature request, please open an issue on GitHub.

## Contact

For questions or help, contact: G.Stavropoulou@tudelft.nl

---

By contributing, you agree that your contributions will be licensed under the Apache License, Version 2.0, and that the maintainers may include your contribution under the project’s copyright.

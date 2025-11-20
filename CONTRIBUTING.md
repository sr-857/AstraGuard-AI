# Contributing to AstraGuard AI

Thank you for your interest in contributing to AstraGuard AI! We welcome contributions from the community to help improve this project.

## 🚀 Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
   ```bash
   git clone https://github.com/your-username/AstraGuard-AI.git
   cd AstraGuard-AI
   ```
3. **Set up** the development environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

## 🔧 Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-number-short-description
   ```

2. Make your changes and ensure tests pass:
   ```bash
   pytest
   ```

3. Format your code:
   ```bash
   black .
   flake8 .
   mypy .
   ```

4. Commit your changes with a descriptive message:
   ```bash
   git commit -m "feat: add new feature"
   # or
   git commit -m "fix: resolve issue with telemetry"
   ```

5. Push your changes to your fork:
   ```bash
   git push origin your-branch-name
   ```

6. Open a Pull Request against the `main` branch

## 📝 Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints for all function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions small and focused on a single responsibility

## 🧪 Testing

- Write unit tests for new features and bug fixes
- Ensure all tests pass before submitting a PR
- Update documentation when adding new features

## 📚 Documentation

- Update relevant documentation when making changes
- Add docstrings to all new functions and classes
- Update README.md if your changes affect the setup or usage

## 🐛 Reporting Issues

When reporting issues, please include:
- A clear description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- System information (OS, Python version, etc.)
- Any relevant error messages or logs

## 🤝 Code of Conduct

Please note that this project is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 📄 License

By contributing to AstraGuard AI, you agree that your contributions will be licensed under the [MIT License](LICENSE).

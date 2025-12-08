# Contributing to Video Analytics Platform

Thank you for your interest in contributing to the Video Analytics Platform! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the project
- Show empathy towards other contributors

## Getting Started

### Prerequisites

- **Node.js** 18+ and npm (for frontend)
- **Python** 3.11+ (for backend services)
- **Docker** and Docker Compose
- **kubectl** (for Kubernetes deployments)
- **AWS CLI** (for infrastructure)
- **Terraform** (for IaC)

### Setting Up Development Environment

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/your-org/virtualization-project.git
   cd virtualization-project
   ```

2. **Set Up Backend Services**
   ```bash
   cd video-analytics
   docker-compose up -d
   ```

3. **Set Up Frontend**
   ```bash
   cd video-analytics/frontend
   npm install
   npm start
   ```

4. **Configure Environment Variables**
   - Copy `.env.example` to `.env` (if available)
   - Update AWS credentials and configuration

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- 'member-number-feature' - To add features

### Creating a Branch

```bash
# For new features
git checkout -b feature/your-feature-name

# For bug fixes
git checkout -b bugfix/issue-description
```

### Making Changes

1. Create a branch from `main` using the naming convention: `member-number-feature-name`
2. Make your changes
3. Write/update tests
4. Update documentation if needed
5. Ensure all tests pass
6. Commit your changes following [commit guidelines](#commit-guidelines)

## Coding Standards

### Python (Backend Services)

- Follow **PEP 8** style guide
- Use **type hints** for function signatures
- Maximum line length: **100 characters**
- Use **Black** formatter (if configured)
- Write **docstrings** for all functions and classes

```python
def process_video(video_id: str, s3_key: str) -> dict:
    """
    Process a video file by transcoding and generating thumbnails.
    
    Args:
        video_id: Unique identifier for the video
        s3_key: S3 object key for the video file
        
    Returns:
        Dictionary containing processing results
    """
    pass
```

### JavaScript/React (Frontend)

- Follow **ESLint** rules
- Use **functional components** with hooks
- Prefer **const** over let, avoid var
- Use **PascalCase** for components, **camelCase** for functions
- Keep components small and focused

```javascript
const VideoCard = ({ video, onSelect }) => {
  return (
    <div className="video-card">
      {/* Component content */}
    </div>
  );
};
```

### Infrastructure (Terraform)

- Use **consistent naming** conventions
- Add **descriptions** to all resources
- Use **variables** for configurable values
- Follow **terraform fmt** formatting

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### Examples

```
feat(uploader): add support for chunked uploads

Implement chunked upload functionality to handle large files
more efficiently. This reduces memory usage and improves
upload reliability for files over 100MB.

Closes #123
```

```
fix(processor): resolve memory leak in FFmpeg transcoding

The processor service was not properly releasing memory after
video transcoding operations. Added explicit cleanup and
resource management.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest changes from `develop`
   ```bash
   git checkout develop
   git pull origin develop
   git checkout your-branch
   git rebase develop
   ```

2. **Run tests locally**
   ```bash
   # Backend
   pytest
   
   # Frontend
   npm test
   ```

3. **Check code quality**
   ```bash
   # Linting
   flake8 .  # Python
   npm run lint  # Frontend
   ```

4. **Update documentation** if your changes affect:
   - API endpoints
   - Configuration
   - Architecture
   - User-facing features

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Security scan passed (Trivy)
- [ ] No breaking changes (or documented)
- [ ] PR template filled out

### PR Description

Use the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md) and provide:
- Clear description of changes
- Link to related issues
- Screenshots/demos for UI changes
- Testing instructions
- Deployment notes

## Testing Requirements



### Manual Testing

- Test in local environment
- Test in staging (if available)
- Verify error handling
- Check performance impact

### Running Tests

```bash
# Backend (Python)
pytest
pytest --cov=video_analytics tests/

# Frontend (React)
npm test
npm run test:coverage
```

## Documentation

### Code Documentation

- Add docstrings to Python functions/classes
- Add JSDoc comments to complex JavaScript functions
- Update README files for new features

### Architecture Documentation

- Update `SYSTEM_ARCHITECTURE.md` for architectural changes
- Update `DEPLOYMENT.md` for deployment changes
- Update `TESTING_GUIDE.md` for testing changes

### API Documentation

- Update API documentation for endpoint changes
- Include request/response examples
- Document error codes and messages

## Security

- **Never commit** secrets, API keys, or credentials
- Use environment variables or secrets management
- Follow security best practices
- Report security issues privately

## Getting Help

- Check existing [documentation](README.md)
- Search [existing issues](../../issues)
- Ask questions in discussions
- Contact maintainers

## Review Process

1. Automated checks must pass (CI/CD)
2. At least one code owner approval required
3. All review comments addressed
4. Tests must pass
5. Maintainer approval for merge

## Questions?

If you have questions or need clarification, please:
- Open an issue with the `question` label
- Reach out to maintainers
- Check project documentation

Thank you for contributing! 🎉

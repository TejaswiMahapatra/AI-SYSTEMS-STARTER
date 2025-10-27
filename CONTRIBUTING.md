# Contributing to AI Systems Starter

First off, thank you for considering contributing to AI Systems Starter! 🎉

It's people like you that make AI Systems Starter such a great tool for the community. We welcome contributions from everyone, whether you're fixing a typo, reporting a bug, or adding a major feature.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Guidelines](#coding-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to fostering an open and welcoming environment. Be respectful, considerate, and constructive in all interactions.

**Our Standards:**
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

Never contributed to open source before? Here are some resources to help you get started:
- [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)
- [First Timers Only](https://www.firsttimersonly.com/)
- [GitHub's Guide to Contributing](https://docs.github.com/en/get-started/quickstart/contributing-to-projects)

**Not sure where to start?** Look for issues labeled:
- \`good first issue\` - Perfect for newcomers
- \`help wanted\` - We'd love your help on these
- \`documentation\` - Improve our docs
- \`bug\` - Fix reported bugs

---

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check if the issue already exists. If it does, add a comment with any additional information.

**When filing a bug report, include:**
- **Clear title** - Describe the issue in one sentence
- **Steps to reproduce** - How did you encounter this bug?
- **Expected behavior** - What should have happened?
- **Actual behavior** - What actually happened?
- **Environment details** - OS, Python version, Docker version
- **Logs/Screenshots** - If applicable
- **Possible fix** - If you have an idea (optional)

**Example:**
\`\`\`markdown
## Bug: Agent timeout on large documents

**Environment:** macOS 14.0, Python 3.11, Docker 24.0

**Steps to reproduce:**
1. Upload a PDF larger than 50 pages
2. Query with agent endpoint
3. Agent times out after 300s

**Expected:** Agent should handle large documents
**Actual:** TimeoutError after 300s

**Logs:**
\`\`\`
ERROR - Ollama request timed out
\`\`\`

**Possible fix:** Implement streaming or chunked processing
\`\`\`

### Suggesting Features

We love new ideas! Before suggesting a feature:
1. Check if it's already been suggested
2. Make sure it aligns with the project's goals
3. Provide a clear use case

**When suggesting features, include:**
- **Problem statement** - What problem does this solve?
- **Proposed solution** - How would you implement it?
- **Alternatives considered** - Other ways to solve it
- **Use cases** - Who benefits from this?

**Example:**
\`\`\`markdown
## Feature: Multi-language document support

**Problem:** Currently only supports English legal documents.

**Proposed Solution:**
- Add language detection in PDF service
- Support multilingual embeddings (e.g., multilingual-MiniLM)
- Update prompts for non-English queries

**Use Cases:**
- International law firms
- Cross-border contracts
- European legal documents

**Alternatives:**
- Translation layer (less accurate)
- Language-specific models (more complex)
\`\`\`

### Improving Documentation

Documentation is crucial! You can help by:
- Fixing typos or unclear explanations
- Adding examples or tutorials
- Translating documentation
- Writing blog posts or guides

**Documentation locations:**
- \`README.md\` - Project overview
- \`docs/getting-started.md\` - Setup guide
- \`ARCHITECTURE.md\` - Technical details
- \`backend/\` - Inline code comments
- \`examples/\` - Usage examples

### Contributing Code

We accept contributions for:
- Bug fixes
- New features
- Performance improvements
- Test coverage
- Code refactoring

**Before starting on major features:**
1. Open an issue to discuss your idea
2. Get feedback from maintainers
3. Align on the approach
4. Then start coding!

This prevents wasted effort if the feature doesn't align with project goals.

---

## Development Setup

### 1. Fork and Clone

\`\`\`bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/ai-systems-starter.git
cd ai-systems-starter

# Add upstream remote
git remote add upstream https://github.com/TejaswiMahapatra/ai-systems-starter.git
\`\`\`

### 2. Set Up Environment

\`\`\`bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start infrastructure
docker-compose -f infra/docker/docker-compose.yml up -d

# Pull Ollama model
docker exec ai-systems-ollama ollama pull llama3.1:8b
\`\`\`

### 3. Create a Branch

\`\`\`bash
# Update your fork
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
\`\`\`

### 4. Make Your Changes

- Write clean, readable code
- Add tests for new functionality
- Update documentation if needed
- Follow existing code style

### 5. Test Your Changes

\`\`\`bash
# Run the system
make run

# Test manually
curl http://localhost:8000/api/v1/health

# Upload a test document
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -F "file=@examples/contracts/sample_clause_contract.pdf" \
  -F "collection_name=TestCollection"

# Test queries
curl -X POST http://localhost:8000/api/v1/query/rag \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key terms?", "collection_name": "TestCollection"}'
\`\`\`

---

## Coding Guidelines

### Python Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with these specifics:

**Code Formatting:**
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use type hints for function parameters and return values
- Add docstrings for all public functions/classes

**Example:**
\`\`\`python
async def process_document(
    file_path: str,
    collection_name: str,
    chunk_size: int = 500
) -> Dict[str, Any]:
    """
    Process a document and store it in the vector database.

    Args:
        file_path: Path to the PDF file
        collection_name: Target Weaviate collection
        chunk_size: Maximum characters per chunk (default: 500)

    Returns:
        Dict containing document_id, num_chunks, and processing time

    Raises:
        FileNotFoundError: If file_path doesn't exist
        ValueError: If collection_name is invalid
    """
    # Implementation here
    pass
\`\`\`

**Naming Conventions:**
- \`snake_case\` for functions and variables
- \`PascalCase\` for classes
- \`UPPER_CASE\` for constants
- Descriptive names (avoid single letters except in loops)

**Good:**
\`\`\`python
def calculate_confidence_score(search_results: List[VectorSearchResult]) -> float:
    avg_score = sum(r.score for r in search_results) / len(search_results)
    return min(avg_score, 1.0)
\`\`\`

**Bad:**
\`\`\`python
def calc(sr):
    s = sum(r.score for r in sr) / len(sr)
    return min(s, 1.0)
\`\`\`

### Async/Await

- Use \`async/await\` for I/O operations
- Don't block the event loop with synchronous operations
- Use \`asyncio.gather()\` for parallel async calls

### Error Handling

- Use specific exception types
- Log errors with context
- Return meaningful error messages

\`\`\`python
try:
    result = await process_document(file_path, collection_name)
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
except Exception as e:
    logger.error(f"Processing failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
\`\`\`

### Testing

When adding tests:
- Write unit tests for individual functions
- Write integration tests for API endpoints
- Use meaningful test names: \`test_should_return_error_when_file_not_found\`
- Mock external dependencies (Ollama, Weaviate)

---

## Commit Messages

Good commit messages help everyone understand the project's history.

**Format:**
\`\`\`
<type>(<scope>): <subject>

<body>

<footer>
\`\`\`

**Types:**
- \`feat\` - New feature
- \`fix\` - Bug fix
- \`docs\` - Documentation changes
- \`style\` - Code style (formatting, no logic change)
- \`refactor\` - Code refactoring
- \`perf\` - Performance improvement
- \`test\` - Adding tests
- \`chore\` - Build process, dependencies

**Examples:**

Good:
\`\`\`
feat(agent): add streaming support for LLM responses

- Implement SSE streaming in agent endpoint
- Update LLM service to use streaming API
- Add progress indicators for long-running queries

Closes #123
\`\`\`

\`\`\`
fix(chunking): preserve clause numbers in nested sections

Previously, nested clauses (e.g., 5.1.1) were not being
captured correctly. Updated regex pattern to handle
multi-level nesting.

Fixes #456
\`\`\`

Bad:
\`\`\`
fix stuff
\`\`\`

\`\`\`
update
\`\`\`

---

## Pull Request Process

### Before Submitting

- Code follows style guidelines
- Self-review completed
- Comments added for complex logic
- Documentation updated
- Tests added/updated
- All tests pass locally
- Commit messages are clear

### Submitting a PR

1. **Push your branch:**
   \`\`\`bash
   git push origin feature/your-feature-name
   \`\`\`

2. **Create Pull Request on GitHub:**
   - Clear title describing the change
   - Reference related issues (\`Fixes #123\`, \`Closes #456\`)
   - Describe what changed and why
   - Include screenshots/demos if UI changes
   - List breaking changes if any

3. **PR Template:**
   \`\`\`markdown
   ## Description
   Brief description of changes

   ## Motivation and Context
   Why is this change needed? What problem does it solve?

   ## How Has This Been Tested?
   Describe your testing approach

   ## Types of changes
   - Bug fix (non-breaking change which fixes an issue)
   - New feature (non-breaking change which adds functionality)
   - Breaking change (fix or feature that causes existing functionality to change)

   ## Checklist
   - My code follows the code style of this project
   - I have updated the documentation accordingly
   - I have added tests to cover my changes
   - All new and existing tests passed

   ## Screenshots (if applicable)
   \`\`\`

### Review Process

1. Maintainers will review within 2-3 days
2. Address feedback by pushing new commits
3. Once approved, your PR will be merged
4. Your contribution will be credited in release notes!

**During review:**
- Be open to feedback
- Respond to comments
- Ask questions if unclear
- Be patient and respectful

---

## Community

### Get Help

- **GitHub Discussions** - Ask questions, share ideas
- **GitHub Issues** - Bug reports, feature requests
- **Email** - tejaswimahapatra208@gmail.com for sensitive topics

### Recognition

All contributors are recognized in:
- \`CONTRIBUTORS.md\` - List of all contributors
- GitHub Contributors page
- Release notes for their contributions

### Stay Updated

- **Watch** the repository for notifications
- **Star** the repo to show support
- Follow updates via GitHub

---

## Questions?

Don't hesitate to ask! The only bad question is the one not asked.

- Open a [GitHub Discussion](https://github.com/TejaswiMahapatra/ai-systems-starter/discussions)
- Comment on relevant issues
- Reach out to maintainers

---

**Thank you for contributing to AI Systems Starter!** 🚀

Every contribution, no matter how small, makes a difference. We're excited to see what you'll build with us!

---

*This guide is inspired by contributing guides from other open-source projects.*

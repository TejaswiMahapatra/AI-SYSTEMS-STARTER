# Video Tutorial Template

Use this template to script your video explanations for each file/concept.

---

## Template Structure

```markdown
# [Video Title]

**Duration**: [Estimated minutes]
**Difficulty**: [Beginner/Intermediate/Advanced]
**Prerequisites**: [What viewer should know]

## Video Outline

### Part 1: Introduction (0:00-2:00)
- What we're building in this video
- Why it matters
- What you'll learn

### Part 2: Concepts Explained (2:00-X:XX)
- Key concept 1
  - What is it?
  - Why do we use it?
  - Alternatives and tradeoffs

- Key concept 2
  - ...

### Part 3: Code Walkthrough (X:XX-Y:YY)
**File**: path/to/file.py

**Line-by-Line**:
- Lines 1-10: [Purpose]
  ```python
  [Code snippet]
  ```
  **Explanation**: ...
  **Why this way**: ...

### Part 4: Running & Testing (Y:YY-Z:ZZ)
- Commands to run
- Expected output
- How to verify it works
- Common errors and fixes

### Part 5: Summary & Next Steps (Z:ZZ-End)
- What we built
- Key takeaways
- Preview of next video

## Timestamps for Description

```
0:00 Introduction
2:00 Concept: [Name]
5:30 Code Walkthrough
12:00 Running the code
15:00 Summary
```

## Resources Mentioned

- Link to GitHub code
- Link to documentation
- Related videos

## Quiz Questions (for engagement)

1. Why did we choose X over Y?
2. What would happen if we removed line Z?
3. How would you modify this for [use case]?
```

---

## Example: Day 2, File 1

# Understanding Pydantic Settings in FastAPI

**Duration**: 18 minutes
**Difficulty**: Intermediate
**Prerequisites**: Basic Python, environment variables

## Video Outline

### Part 1: Introduction (0:00-2:00)

"In this video, we're diving into `backend/config.py` - the brain of our application that handles all configuration. By the end, you'll understand why we use Pydantic Settings instead of simple environment variables, and how it makes our code safer and easier to maintain."

**Show on screen**:
- File: backend/config.py
- Line count: 190 lines
- Purpose: Type-safe configuration

### Part 2: The Problem with os.getenv (2:00-5:00)

"Before we look at our solution, let's understand the problem. Here's the old way:"

```python
import os

# Old way - error prone!
port = os.getenv("PORT", "8000")  # Returns string!
port = int(port)  # Manual parsing - what if it fails?

if port < 0 or port > 65535:  # Manual validation
    raise ValueError("Invalid port")

# No type hints, no IDE help
```

**Problems**:
1. Everything is a string (need manual parsing)
2. No type checking (typos caught at runtime)
3. Manual validation (easy to forget)
4. No IDE autocomplete
5. Hard to test

### Part 3: Enter Pydantic Settings (5:00-8:00)

"Pydantic Settings solves all these problems. Let's see how:"

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    port: int = 8000  # Type hint! Auto-parsed!
    # Pydantic validates: must be int, auto-converts from env

    model_config = SettingsConfigDict(
        env_file=".env",           # Auto-load from .env
        case_sensitive=False,       # PORT or port both work
        extra="ignore"              # Ignore unknown vars
    )
```

**Benefits**:
1. Type safety (int is int, not string)
2. Auto-parsing (string → int)
3. Validation on startup (fail fast)
4. IDE autocomplete (knows port is int)
5. Easy to test (just create Settings object)

### Part 4: Code Walkthrough - config.py (8:00-15:00)

**Lines 1-10: Imports**
```python
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
```

**Explanation**:
- `Literal` for enum-like choices (only specific values allowed)
- `Optional` for values that might be None
- `BaseSettings` is the magic class from Pydantic

---

**Lines 12-22: Settings Class Definition**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
```

**Explanation**:
- `env_file=".env"` - Auto-load from .env file
- `case_sensitive=False` - PORT or port both work
- `extra="ignore"` - Don't error on unknown env vars

**Why this way**: In production, you might have extra env vars from Docker/K8s. `extra="ignore"` prevents errors.

---

**Lines 24-31: Application Settings**
```python
app_name: str = "AI Systems Starter"
app_version: str = "0.1.0"
environment: Literal["development", "staging", "production"] = "development"
debug: bool = True
```

**Explanation**:
- `Literal["development", "staging", "production"]` - Only these 3 values allowed!
- Try setting `ENVIRONMENT=testing` → Pydantic will error on startup
- `debug: bool` - Auto-converts "true"/"false" string to Python bool

**Why Literal**: Catches typos early. If you typo "developmen" in .env, app won't start (good!)

---

**Lines 50-56: Computed Properties**
```python
@property
def database_url(self) -> str:
    """Construct async PostgreSQL URL."""
    return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
```

**Explanation**:
- `@property` - Computed value (not stored in .env)
- Builds connection string from parts
- Different URL for async vs sync (asyncpg vs psycopg2)

**Why separate parts**:
1. Easier to override just host or port
2. Can reuse parts (same host for sync and async)
3. Clearer in .env file

---

**Lines 87-91: LLM Provider Choice**
```python
llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"

ollama_url: str = "http://localhost:11434"
ollama_model: str = "llama3.1:8b"
```

**Explanation**:
- Defaults to "ollama" (open source)
- Can change to "openai" without code changes
- Each provider has its own settings

**Why Literal**: Type-safe provider switching. Code can do:
```python
if settings.llm_provider == "ollama":
    # IDE knows this is valid!
```

---

**Lines 160-176: Validation Function**
```python
def validate_settings():
    """Validate critical configuration settings."""
    errors = []

    if settings.llm_provider == "openai" and not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(errors))
```

**Explanation**:
- Custom validation beyond type checking
- Checks logical constraints (if A then B)
- Called on startup (in main.py lifespan)

**Why needed**: Pydantic validates types, but not business logic. This catches: "You chose OpenAI but forgot the API key!"

### Part 5: How It All Connects (15:00-17:00)

**In .env file**:
```bash
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

**In main.py (startup)**:
```python
from backend.config import settings, validate_settings

# On startup
validate_settings()  # Check everything is valid

# Throughout code
print(settings.llm_provider)  # "ollama"
print(settings.database_url)  # "postgresql+asyncpg://..."
```

**To switch to OpenAI**:
```bash
# Just change .env, no code changes!
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**That's it! Code automatically uses OpenAI now.**

### Part 6: Testing It (17:00-18:00)

**Command**:
```bash
cd backend
python -c "from config import settings; print(settings.database_url)"
```

**Expected output**:
```
postgresql+asyncpg://postgres:postgres@localhost:5432/ai_systems
```

**Try changing .env**:
```bash
POSTGRES_HOST=192.168.1.100
```

**Run again**:
```
postgresql+asyncpg://postgres:postgres@192.168.1.100:5432/ai_systems
```

**It works! No code changes needed.**

### Part 7: Summary & Key Takeaways (18:00-20:00)

**What we learned**:
1. **Pydantic Settings** > os.getenv for production
2. **Type safety** catches errors early
3. **Literal types** for enum-like choices
4. **Properties** for computed values
5. **Validation** for business logic

**Why it matters**:
- Safer code (type checked)
- Better DX (IDE autocomplete)
- Easier to change (just .env file)
- Self-documenting (types show what's needed)

**Next video**: We'll use these settings in `core/database.py` to connect to PostgreSQL.

## Timestamps for Description

```
0:00 Introduction
2:00 Problem: os.getenv limitations
5:00 Solution: Pydantic Settings
8:00 Code Walkthrough: Line by line
15:00 How it all connects
17:00 Testing it yourself
18:00 Summary & Takeaways
```

## Resources

- Code: https://github.com/TejaswiMahapatra/ai-systems-starter/blob/main/backend/config.py
- Pydantic Settings Docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Next: database.py walkthrough

## Quiz Questions

1. Why use `Literal["ollama", "openai"]` instead of just `str`?
   - Catches typos at startup vs runtime errors

2. What happens if you set `PORT=invalid` in .env?
   - Pydantic validation error on startup (good!)

3. How would you add a new LLM provider (e.g., Gemini)?
   - Add "gemini" to Literal, add gemini_api_key field, update validation

---


# GitHub Repository Setup Guide

This guide will help you complete the setup of your Clause.AI repository for open source collaboration.

## ✅ Already Completed

- [x] CONTRIBUTING.md created
- [x] GitHub Discussions enabled
- [x] Issue templates (bug report, feature request)
- [x] Pull request template
- [x] CONTRIBUTORS.md
- [x] CI/CD workflow

## 📋 Manual Steps Required on GitHub

### 1. Create Labels

Go to: **Settings → Labels** and create these labels:

#### Priority Labels
```
🔴 priority: critical    #d73a4a
🟠 priority: high        #e99695
🟡 priority: medium      #fbca04
🟢 priority: low         #d4c5f9
```

#### Type Labels
```
🐛 bug                   #d73a4a
✨ enhancement           #a2eeef
📝 documentation         #0075ca
⚡ performance           #fbca04
🔒 security              #ee0701
♻️  refactor             #fff000
🎨 style                 #fef2c0
```

#### Status Labels
```
👀 triage                #d876e3
✅ ready                 #0e8a16
🚧 in progress           #fbca04
🤔 needs info            #d876e3
🎯 good first issue      #7057ff
🙏 help wanted           #008672
❌ wont fix              #ffffff
✔️  done                 #0e8a16
```

#### Area Labels
```
🧠 area: agent           #1d76db
📄 area: chunking        #0052cc
🔍 area: search          #006b75
🐳 area: infrastructure  #5319e7
🎨 area: frontend        #d4c5f9
🗄️  area: database       #0e8a16
```

### 2. Branch Protection Rules

Go to: **Settings → Branches → Add rule**

**For `main` branch:**
- [x] Require a pull request before merging
- [x] Require approvals (1)
- [x] Dismiss stale PR approvals when new commits are pushed
- [x] Require status checks to pass before merging
  - Select: `lint`, `test` (from CI workflow)
- [x] Require conversation resolution before merging
- [x] Include administrators

### 3. Enable GitHub Features

Go to: **Settings → General → Features**

- [x] Wikis (for additional documentation)
- [x] Issues
- [x] Sponsorships (if you want to accept donations)
- [x] Projects (for roadmap tracking)
- [x] Preserve this repository (archive important repos)
- [x] Discussions (already done!)

### 4. Configure Actions

Go to: **Settings → Actions → General**

- Workflow permissions: **Read and write permissions**
- [x] Allow GitHub Actions to create and approve pull requests

### 5. Set Up Projects (Optional but Recommended)

Create a new Project: **Settings → Projects → New project**

**Project name:** Clause.AI Roadmap

**Columns:**
1. 📋 Backlog
2. 🎯 To Do
3. 🚧 In Progress
4. 👀 In Review
5. ✅ Done

### 6. Create Milestones

Go to: **Issues → Milestones → New milestone**

**Suggested milestones:**
- v0.2.0 - Frontend Development
- v0.3.0 - Test Coverage & Quality
- v0.4.0 - Production Ready
- v1.0.0 - Stable Release

### 7. Repository Description

Update the repository description:

```
Open-source RAG system for legal documents with clause-aware chunking, vector search, and LangGraph agents. 100% local with Ollama.
```

**Topics to add:**
```
rag, llm, legal-tech, weaviate, langchain, langgraph, ollama, fastapi, 
vector-database, document-ai, python, docker, open-source
```

### 8. Repository Settings

Go to: **Settings → General**

**Social preview:**
- Upload a banner image (1280x640px) showing Clause.AI architecture diagram

**Features to disable:**
- [ ] Wikis (if you prefer using /docs folder)
- [ ] Projects (if using external project management)

## 🚀 Creating Your First "Good First Issue"

Here are 5 ready-to-post "good first issue" tasks:

### Issue 1: Add Health Check Endpoint Tests
```markdown
**Title:** Add unit tests for health check endpoint

**Description:**
We need test coverage for the `/api/v1/health` endpoint.

**Tasks:**
- [ ] Create `backend/tests/test_health.py`
- [ ] Add test for successful health check response
- [ ] Add test for response structure validation
- [ ] Ensure tests pass in CI

**Expected files:**
- `backend/tests/test_health.py`

**Hints:**
- Use `pytest` and `pytest-asyncio`
- Check `backend/api/v1/health.py` for the endpoint implementation
- Mock dependencies if needed

**Labels:** `good first issue`, `test`, `area: backend`
```

### Issue 2: Add Logging to Chunking Service
```markdown
**Title:** Improve logging in chunking service

**Description:**
Add more detailed logging to help debug clause-aware chunking issues.

**Tasks:**
- [ ] Add debug logs when clauses are detected
- [ ] Log statistics (total chunks, clause chunks, regular chunks)
- [ ] Add warning when clause patterns aren't found

**Expected changes:**
- `backend/services/chunking_service.py`

**Example:**
```python
logger.debug(f"Detected clause {clause_number} in section {section_title}")
logger.info(f"Chunking complete: {total_chunks} total, {clause_chunks} with metadata")
```

**Labels:** `good first issue`, `enhancement`, `area: chunking`
```

### Issue 3: Add Environment Variable Validation
```markdown
**Title:** Validate required environment variables on startup

**Description:**
Check that all required environment variables are set when the backend starts.

**Tasks:**
- [ ] Create function to validate required env vars
- [ ] Call validation in `backend/main.py` startup
- [ ] Print helpful error messages for missing vars
- [ ] Add tests

**Required variables to check:**
- POSTGRES_HOST
- POSTGRES_PORT
- REDIS_HOST
- WEAVIATE_URL
- OLLAMA_URL

**Labels:** `good first issue`, `enhancement`, `area: infrastructure`
```

### Issue 4: Create Examples Directory
```markdown
**Title:** Add usage examples to /examples directory

**Description:**
Create example scripts showing how to use Clause.AI programmatically.

**Tasks:**
- [ ] Create `examples/` directory
- [ ] Add `examples/basic_rag_query.py` - Simple RAG query
- [ ] Add `examples/agent_query.py` - Using the agent
- [ ] Add `examples/batch_upload.py` - Upload multiple documents
- [ ] Add README.md explaining each example

**Labels:** `good first issue`, `documentation`
```

### Issue 5: Add Query Performance Metrics
```markdown
**Title:** Log query performance metrics

**Description:**
Track how long different operations take to help identify bottlenecks.

**Tasks:**
- [ ] Add timing decorator for key functions
- [ ] Log metrics for:
  - Embedding generation time
  - Vector search time
  - LLM generation time
  - Total query time
- [ ] Include in query response metadata

**Expected changes:**
- `backend/services/llm_service.py`
- `backend/services/embedding_service.py`
- `backend/services/vector_service.py`

**Labels:** `good first issue`, `enhancement`, `performance`
```

## 📊 Analytics Setup (Optional)

Consider adding:
- **Plausible.io** or **Simple Analytics** - Privacy-friendly analytics
- **GitHub Insights** - Built-in traffic and clone stats
- **Star History** - Embed star history chart in README

## 🎯 Launch Checklist

Before announcing your project:

- [ ] All documentation is complete and up-to-date
- [ ] README has clear setup instructions
- [ ] Demo video recorded (3-5 min)
- [ ] 5-10 "good first issue" tasks created
- [ ] CI/CD is working
- [ ] All labels are created
- [ ] Repository description and topics set
- [ ] License file present (Apache 2.0)
- [ ] Social preview image uploaded

## 📢 Launch Announcement Template

**Title:** Clause.AI - Open Source RAG System for Legal Documents

**Body:**
```markdown
I've been working on Clause.AI for the past few months, and I'm excited to open source it today! 🚀

## What is Clause.AI?

An open-source RAG (Retrieval-Augmented Generation) system specifically designed for legal documents. Unlike generic document AI systems, Clause.AI preserves the hierarchical structure of contracts during chunking (Articles, Sections, Clauses).

## Key Features

✅ Clause-aware chunking - Preserves legal document structure
✅ Vector search with Weaviate
✅ Human-friendly AI responses (not robotic!)
✅ LangGraph agents for complex queries
✅ 100% local with Ollama (no API keys needed!)
✅ Real-time progress updates via Redis Pub/Sub
✅ Docker Compose for easy setup

## Perfect For

- Law firms analyzing contracts
- Students learning RAG systems
- Developers building document AI
- Anyone working with structured documents

## Tech Stack

FastAPI • Weaviate • LangGraph • Ollama • Docker • PostgreSQL • Redis

## Getting Started

```bash
git clone https://github.com/TejaswiMahapatra/ai-systems-starter
cd ai-systems-starter
make run
```

That's it! No API keys, no sign-ups, everything runs locally.

## Looking for Contributors!

This is a community project - contributions of all kinds are welcome! Check out issues labeled "good first issue" to get started.

**GitHub:** https://github.com/TejaswiMahapatra/ai-systems-starter
**Demo:** [link to demo video]
**Docs:** [link to getting started]

What would you use Clause.AI for? Let me know in the comments! 💬
```

## 🎉 Post-Launch

Week 1:
- Respond to all issues/PRs within 24 hours
- Thank contributors publicly
- Create weekly update thread

Week 2:
- Blog post: "Building Clause.AI: Lessons Learned"
- Share contributor spotlight

Month 1:
- Monthly update with stats and highlights
- Review and update roadmap
- Celebrate milestones (stars, contributors, etc.)

---

**Questions?** Open a discussion or reach out!

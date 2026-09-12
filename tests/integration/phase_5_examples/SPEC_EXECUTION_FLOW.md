# 📋 EXECUTION FLOW SPECIFICATION

**What:** Define requirements for testing EXECUTION flow
**Implementation:** Language/framework-agnostic
**Examples:** Python, JavaScript, Bash, Go (provided)

---

## 🎯 Test Purpose

Validate that the **EXECUTION flow structure** is complete and production-ready.

The test should:
1. ✅ Check **entry points** exist
2. ✅ Validate **CANONICAL layer** (immutable authority)
3. ✅ Check **Guides layer** (operational help)
4. ✅ Verify **Runtime layer** (search indices)
5. ✅ Confirm **Custom layer** (project-specific)
6. ✅ Test **Markdown links** validity
7. ✅ Verify **AI-first design** (root level)

---

## 📋 TEST 1: Entry Points

### What to test:
Framework entry points exist and are accessible

### Requirements:
Verify these files exist in `EXECUTION/`:
- [ ] `README.md` — Main documentation
- [ ] `_START_HERE.md` — New user guide
- [ ] `NAVIGATION.md` — Document finder
- [ ] `INDEX.md` — Full index

### Success criteria:
All 4 files exist and are readable

### Expected output:
```
✅ Entry point found: README.md
✅ Entry point found: _START_HERE.md
✅ Entry point found: NAVIGATION.md
✅ Entry point found: INDEX.md
```

---

## 📋 TEST 2: CANONICAL Layer

### What to test:
Immutable authority layer is complete

### Requirements:

#### Rules Layer:
- [ ] `docs/ia/CANONICAL/rules/constitution.md` — 15 principles
- [ ] `docs/ia/CANONICAL/rules/ia-rules.md` — 16 mandatory rules
- [ ] `docs/ia/CANONICAL/rules/conventions.md` — Code conventions

#### Decisions Layer (ADRs):
- [ ] At least 6 files matching: `docs/ia/CANONICAL/decisions/ADR-*.md`

#### Specifications Layer:
- [ ] `docs/ia/CANONICAL/specifications/definition_of_done.md`
- [ ] `docs/ia/CANONICAL/specifications/communication.md`
- [ ] `docs/ia/CANONICAL/specifications/architecture.md`
- [ ] `docs/ia/CANONICAL/specifications/testing.md`

### Success criteria:
- All rules files exist
- At least 6 ADR files found
- All specification files exist

### Expected output:
```
🔴 Constitution Layer:
  ✅ rules/constitution.md
  ✅ rules/ia-rules.md
  ✅ rules/conventions.md

🟡 Decisions Layer (ADRs):
  ✅ Found 6 ADRs

🟢 Specifications Layer:
  ✅ specifications/definition_of_done.md
  ✅ specifications/communication.md
  ✅ specifications/architecture.md
  ✅ specifications/testing.md
```

---

## 📋 TEST 3: Guides Layer

### What to test:
Operational guides are complete

### Requirements:

#### Onboarding Guides:
- [ ] `docs/ia/guides/onboarding/AGENT_HARNESS.md`
- [ ] `docs/ia/guides/onboarding/VALIDATION_QUIZ.md`

#### Operational Guides:
- [ ] `docs/ia/guides/operational/ADDING_NEW_PROJECT.md`
- [ ] `docs/ia/guides/operational/TROUBLESHOOTING_SPEC_VIOLATIONS.md`

#### Emergency Procedures:
- [ ] `docs/ia/guides/emergency/README.md`

#### Reference Guides:
- [ ] `docs/ia/guides/reference/FAQ.md`
- [ ] `docs/ia/guides/reference/GLOSSARY.md`

### Success criteria:
- At least 2 onboarding guides
- At least 2 operational guides
- At least 1 emergency guide
- At least 2 reference guides

### Expected output:
```
📚 ONBOARDING:
  ✅ AGENT_HARNESS.md
  ✅ VALIDATION_QUIZ.md

📚 OPERATIONAL:
  ✅ ADDING_NEW_PROJECT.md
  ✅ TROUBLESHOOTING_SPEC_VIOLATIONS.md

📚 EMERGENCY:
  ✅ README.md

📚 REFERENCE:
  ✅ FAQ.md
  ✅ GLOSSARY.md
```

---

## 📋 TEST 4: Runtime Layer

### What to test:
Search and index files exist

### Requirements:
These files must exist in `docs/ia/runtime/`:
- [ ] `search-keywords.md` — Keyword mapping for docs
- [ ] `spec-canonical-index.md` — CANONICAL quick reference
- [ ] `spec-guides-index.md` — Guides quick reference

### Success criteria:
All 3 runtime index files exist and are readable

### Expected output:
```
✅ search-keywords.md (142 lines, 6307 bytes)
✅ spec-canonical-index.md (181 lines, 5634 bytes)
✅ spec-guides-index.md (242 lines, 8156 bytes)
```

---

## 📋 TEST 5: Custom Layer

### What to test:
Project-specific customization structure exists

### Requirements:
- [ ] Directory exists: `docs/ia/custom/`
- [ ] At least 1 project subdirectory exists

### Success criteria:
Custom layer directory exists and has content

### Expected output:
```
✅ Custom layer exists
✅ Projects configured: 1
  - [project-name]
```

---

## 📋 TEST 6: Markdown Links

### What to test:
Internal markdown links are valid

### Requirements:
Check these files for markdown links:
- [ ] `_START_HERE.md` — Should have links
- [ ] `NAVIGATION.md` — Should have many links (50+)
- [ ] `INDEX.md` — Should have many links (50+)

### Link Format:
Links must follow markdown format: `[text](path#L123)`

### Success criteria:
- Files have properly formatted links
- Total link count > 100
- No broken references detected

### Expected output:
```
✅ _START_HERE.md: 13 links found
✅ NAVIGATION.md: 73 links found
✅ INDEX.md: 60 links found
📊 Total links: 146
```

---

## 📋 TEST 7: AI-First Design

### What to test:
AI-first documentation exists at root level

### Requirements:
At root level of framework:
- [ ] `.providence-index.md` — Machine learning seed (for LLMs/agents)
- [ ] `README.md` — Public-facing documentation
- [ ] `.spec.config` — Framework discovery

### Success criteria:
All 3 files exist at root and are readable

### Expected output:
```
✅ .providence-index.md (12548 bytes)
✅ README.md (7859 bytes)
✅ .spec.config (1333 bytes)
```

---

## 🎯 Overall Test Result

### Pass Criteria:
- 90%+ of checks pass ✅
- All critical checks pass (entry points, CANONICAL, guides, runtime)
- Links are valid
- AI-first design complete

### Expected Final Output:
```
Tests Passed: 29/29

✅ EXECUTION FLOW: READY FOR PRODUCTION
```

### Fail Result:
```
Tests Passed: 20/29

❌ EXECUTION FLOW: CHECK FAILURES ABOVE
```

---

## 🔧 Implementation Guidelines

### File Discovery:
- [ ] Use file system API to check file existence
- [ ] Use file globbing for pattern matching (ADR-*.md)
- [ ] Count matching files

### Content Validation:
- [ ] Read file contents where needed
- [ ] Parse markdown links: `\[([^\]]+)\]\(([^)]+)\)`
- [ ] Count total links

### Error Handling:
- [ ] Catch file not found errors
- [ ] Report specific missing files
- [ ] Continue testing other sections if possible

### Reporting:
- [ ] Report each test clearly
- [ ] Show results for each subcategory
- [ ] Provide file counts/sizes where relevant
- [ ] Summary with pass/fail count
- [ ] Exit code: 0 (≥90% pass), 1 (< 90% pass)

---

## 📝 Implementation in Your Language

Choose implementation based on your tech stack:

### Python
See: `examples/python/example_execution_flow.py`

### JavaScript/TypeScript
See: `examples/javascript/test-execution-flow.js`

### Bash/Shell
See: `examples/bash/test-execution-flow.sh`

### Go
See: `examples/go/test_execution_flow.go`

### Other
Follow the spec above with your language's idioms

---

**Framework-Agnóstic Testing**
Specification defines WHAT, implementation defines HOW

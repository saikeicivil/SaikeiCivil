# Saikei Civil — GitHub Migration Plan
## Transitioning from Saikei Civil to Saikei Civil

**Date:** December 4, 2025  
**Status:** PLANNING  
**Risk Level:** Low (early in project lifecycle)

---

## Executive Summary

This document outlines the complete migration strategy for renaming Saikei Civil to Saikei Civil across GitHub, codebase, and all related assets. The migration is relatively low-risk because:

1. Project is early (4 of 16 sprints complete)
2. Limited external dependencies/users
3. GitHub provides automatic redirects for renamed repos
4. No package registry (PyPI) presence yet

---

## Part 1: Migration Overview

### What Needs to Change

| Category | Current | New |
|----------|---------|-----|
| **GitHub Org** | (personal repo) | github.com/saikeicivil |
| **Repository** | Saikei Civil | saikei |
| **Folder name** | saikei | saikei |
| **Extension ID** | saikei_civil | saikei_civil |
| **Display name** | Saikei Civil | Saikei Civil |
| **Operator prefix** | saikei. | saikei. |
| **Panel prefix** | SAIKEI_ | SAIKEI_ |

### Migration Phases

```
Phase 1: Preparation (Before Migration)
    ↓
Phase 2: GitHub Organization Setup
    ↓
Phase 3: Codebase Refactoring
    ↓
Phase 4: Repository Transfer
    ↓
Phase 5: Post-Migration Cleanup
    ↓
Phase 6: Announcement & Redirect Setup
```

---

## Part 2: Pre-Migration Checklist

### ✅ Assets to Secure FIRST (Do This NOW)

- [ ] Register domain: saikeicivil.org
- [ ] Register domain: saikeicivil.com (protection)
- [ ] Create GitHub organization: github.com/saikeicivil
- [ ] Reserve social handles: @saikeicivil

### 📋 Inventory Current State

**Repository location:**
```
C:\Users\amish\OneDrive\OneDrive Documents\GitHub\Saikei Civil\saikei
```

**Current structure:**
```
Saikei Civil/                    ← Repository root
└── saikei/                ← Extension folder (becomes saikei/)
    ├── __init__.py
    ├── blender_manifest.toml
    ├── core/
    │   ├── __init__.py
    │   ├── native_ifc_alignment.py
    │   ├── native_ifc_georeferencing.py
    │   ├── alignment_visualizer.py
    │   ├── crs_searcher.py
    │   ├── dependency_manager.py
    │   └── ...
    ├── operators/
    │   ├── __init__.py
    │   ├── alignment_operators.py
    │   ├── georef_operators.py
    │   ├── pi_operators.py
    │   └── ...
    ├── ui/
    │   ├── __init__.py
    │   ├── alignment_panel.py
    │   ├── georef_properties.py
    │   ├── panels/
    │   └── ...
    ├── visualization/
    ├── tests/
    └── README.md
```

---

## Part 3: Detailed Migration Steps

### Phase 1: Preparation (1-2 hours)

#### Step 1.1: Create Full Backup
```bash
# Create timestamped backup
cd "C:\Users\amish\OneDrive\OneDrive Documents\GitHub"
xcopy /E /I Saikei Civil Saikei Civil_backup_20251204
```

#### Step 1.2: Document Current State
- [ ] Note current commit hash
- [ ] Export issues list (if any)
- [ ] Save current GitHub stars/forks count
- [ ] Screenshot current README

#### Step 1.3: Prepare Find/Replace List
Create a checklist of all strings to replace:

| Find | Replace | Context |
|------|---------|---------|
| `Saikei Civil` | `Saikei Civil` | Display names, docs |
| `saikei` | `saikei` | Code identifiers |
| `SAIKEI` | `SAIKEI` | Constants, panel IDs |
| `saikei_civil` | `saikei_civil` | Extension ID |
| `saikei.` | `saikei.` | Operator bl_idname |

---

### Phase 2: GitHub Organization Setup (30 minutes)

#### Step 2.1: Create Organization
1. Go to github.com → Your profile → Organizations → New
2. Organization name: `saikeicivil`
3. Contact email: your email
4. Plan: Free (sufficient for open source)

#### Step 2.2: Configure Organization
- [ ] Add profile picture (temporary — use placeholder until logo ready)
- [ ] Add description: "Open-source native IFC civil engineering tools"
- [ ] Add website: saikeicivil.org (once registered)
- [ ] Set default repository permissions

#### Step 2.3: Create Team Structure (Optional)
- `maintainers` — Full access
- `contributors` — Write access
- `community` — Read + discussions

---

### Phase 3: Codebase Refactoring (2-4 hours)

This is the most critical phase. Do this BEFORE transferring the repository.

#### Step 3.1: Update blender_manifest.toml

**Current:**
```toml
schema_version = "1.0.0"

id = "saikei_civil"
name = "Saikei Civil"
tagline = "Native IFC civil engineering design tools"
version = "0.5.0"
type = "add-on"

maintainer = "Desert Springs CE, Michael Yoder"
```

**New:**
```toml
schema_version = "1.0.0"

id = "saikei_civil"
name = "Saikei Civil"
tagline = "Native IFC civil engineering design — the landscape around the buildings"
version = "0.6.0"  # Bump version for rebrand
type = "add-on"

maintainer = "Desert Springs CE, Michael Yoder"
website = "https://saikeicivil.org"
```

#### Step 3.2: Rename Extension Folder
```bash
# In repository root
cd "C:\Users\amish\OneDrive\OneDrive Documents\GitHub\Saikei Civil"
git mv saikei saikei
```

#### Step 3.3: Update __init__.py

**Key changes in main __init__.py:**
```python
# Old
bl_info = {
    "name": "Saikei Civil",
    "author": "Desert Springs CE",
    "description": "Native IFC civil engineering design tools",
    ...
}

# New
bl_info = {
    "name": "Saikei Civil",
    "author": "Desert Springs CE", 
    "description": "Native IFC civil engineering design — the landscape around the buildings",
    ...
}
```

#### Step 3.4: Update All Operator bl_idname Values

**Pattern to find:**
```python
bl_idname = "saikei.some_operator"
```

**Replace with:**
```python
bl_idname = "saikei.some_operator"
```

**Files to update:**
- `operators/alignment_operators.py`
- `operators/georef_operators.py`
- `operators/pi_operators.py`
- `operators/file_operators.py`
- `operators/validation_operators.py`
- `operators/visualization_operators.py`
- Any other operator files

#### Step 3.5: Update All Panel bl_idname Values

**Pattern to find:**
```python
bl_idname = "SAIKEI_PT_some_panel"
```

**Replace with:**
```python
bl_idname = "SAIKEI_PT_some_panel"
```

**Files to update:**
- `ui/alignment_panel.py`
- `ui/dependency_panel.py`
- `ui/validation_panel.py`
- `ui/panels/georeferencing_panel.py`
- `ui/panels/visualization_panel.py`
- Any other panel files

#### Step 3.6: Update Property Group Names

**Pattern:**
```python
class SaikeiCivilSettings(bpy.types.PropertyGroup):
```

**Replace:**
```python
class SaikeiSettings(bpy.types.PropertyGroup):
```

Also update registration:
```python
# Old
bpy.types.Scene.saikei = PointerProperty(type=SaikeiCivilSettings)

# New  
bpy.types.Scene.saikei = PointerProperty(type=SaikeiSettings)
```

#### Step 3.7: Update Import Statements

Any file that imports from the package:
```python
# Old
from saikei.core import native_ifc_alignment

# New
from saikei.core import native_ifc_alignment
```

#### Step 3.8: Update Documentation

**Files to update:**
- `README.md` — Full rewrite with new branding
- All markdown files in project knowledge
- Code comments mentioning "Saikei Civil"
- Docstrings

#### Step 3.9: Run Tests
```bash
# Ensure nothing broke
cd saikei
python -m pytest tests/ -v
```

#### Step 3.10: Commit All Changes
```bash
git add -A
git commit -m "Rebrand: Saikei Civil → Saikei Civil

- Rename extension folder: saikei → saikei
- Update extension ID: saikei_civil → saikei_civil
- Update all operator bl_idname prefixes
- Update all panel bl_idname prefixes  
- Update property group names
- Update documentation and README
- Bump version to 0.6.0

This rebrand aligns with Blender Foundation trademark requirements
and positions Saikei Civil as the horizontal/infrastructure
complement to Bonsai's vertical/building BIM focus.

See: saikeicivil.org for more information"
```

---

### Phase 4: Repository Transfer (15 minutes)

#### Option A: Transfer Existing Repository (Recommended)

1. **Rename repository first:**
   - Go to repository Settings → General
   - Change name from `Saikei Civil` to `saikei`
   - GitHub will create automatic redirect

2. **Transfer to organization:**
   - Settings → Danger Zone → Transfer ownership
   - Select `saikeicivil` organization
   - Confirm transfer

3. **Result:** `github.com/saikeicivil/saikei`

#### Option B: Fresh Start (Alternative)

If you prefer a clean slate:

1. Create new repo in organization: `github.com/saikeicivil/saikei`
2. Push refactored code to new repo
3. Archive old repository (don't delete — preserve history)

**Pros of Option B:**
- Clean commit history from rebrand forward
- No "Saikei Civil" in git log

**Cons of Option B:**
- Lose stars/forks
- Links to old repo won't redirect

**Recommendation:** Use Option A — history is valuable, and GitHub redirects handle old links.

---

### Phase 5: Post-Migration Cleanup (1 hour)

#### Step 5.1: Update Local Development Environment

```bash
# Update remote URL
cd "C:\Users\amish\OneDrive\OneDrive Documents\GitHub\saikei"
git remote set-url origin https://github.com/saikeicivil/saikei.git

# Verify
git remote -v
```

#### Step 5.2: Update Blender Symlink

If you use a symlink for development:
```bash
# Remove old symlink
rmdir "%APPDATA%\Blender Foundation\Blender\4.5\extensions\saikei_civil"

# Create new symlink
mklink /D "%APPDATA%\Blender Foundation\Blender\4.5\extensions\saikei_civil" "C:\Users\amish\OneDrive\OneDrive Documents\GitHub\saikei\saikei"
```

#### Step 5.3: Update GitHub Repository Settings

- [ ] Add topics: `blender`, `ifc`, `civil-engineering`, `bim`, `open-source`, `infrastructure`
- [ ] Update description
- [ ] Add website URL
- [ ] Enable Discussions (if desired)
- [ ] Set up branch protection rules

#### Step 5.4: Create GitHub Release

```markdown
## v0.6.0 — Saikei Civil (Rebrand Release)

🎉 **Saikei Civil is now Saikei Civil!**

### Why the name change?
- Compliance with Blender Foundation trademark requirements
- "Saikei" (栽景) means "planted landscape" in Japanese
- Natural complement to Bonsai (buildings) — Saikei shapes the infrastructure around them

### What's the same?
- All functionality preserved
- Same great open-source civil engineering tools
- Same native IFC approach

### Migration notes:
- Extension ID changed: `saikei_civil` → `saikei_civil`
- You may need to reinstall the extension

**Full changelog:** [link]
```

---

### Phase 6: Announcement & Communication (1 hour)

#### Step 6.1: Update Project Knowledge Files

All the markdown files in your project folder need "Saikei Civil" → "Saikei Civil" updates.

#### Step 6.2: Announcement Posts

**OSArch Forum:**
```markdown
# Saikei Civil is now Saikei Civil! 🌿

Following the Blender Foundation's trademark requirements (and inspired by 
the BlenderBIM → Bonsai transition), we're excited to announce that 
Saikei Civil is now **Saikei Civil**!

## Why "Saikei"?

Saikei (栽景) is a Japanese art form meaning "planted landscape" — while 
bonsai focuses on a single tree (vertical), saikei creates entire miniature 
landscapes with terrain, paths, and water features (horizontal).

This perfectly captures what we do: **the infrastructure around the buildings**.

- 🌳 Bonsai = Buildings (vertical BIM)
- 🏗️ Saikei = Infrastructure (horizontal civil)

## What's changing?
- Name and branding only
- All code and functionality preserved
- New home: github.com/saikeicivil/saikei

## What's NOT changing?
- Open source commitment
- Native IFC approach  
- Development velocity
- Community focus

Thanks for your support! 🙏
```

**LinkedIn/Twitter:**
```
🌿 Announcing: Saikei Civil → Saikei Civil

Following Blender's trademark requirements, we're rebranding!

Saikei (栽景) = "planted landscape" in Japanese

While Bonsai crafts buildings, Saikei shapes the world around them.
Roads, earthwork, drainage — all native IFC, all open source.

🔗 saikeicivil.org
#OpenBIM #CivilEngineering #Blender #OpenSource
```

---

## Part 4: File-by-File Change Reference

### Critical Files (Must Update)

| File | Changes Required |
|------|------------------|
| `blender_manifest.toml` | id, name, tagline, website |
| `__init__.py` (main) | bl_info, imports |
| `operators/*.py` | All bl_idname values |
| `ui/*.py` | All bl_idname values |
| `ui/panels/*.py` | All bl_idname values |
| `README.md` | Complete rewrite |

### Search Patterns for Global Find/Replace

Run these searches across the entire codebase:

```
# Case-sensitive searches
"Saikei Civil" → "Saikei Civil"
"saikei" → "saikei"
"SAIKEI" → "SAIKEI"
"saikei_civil" → "saikei_civil"

# Operator patterns
'saikei.' → 'saikei.'
"saikei." → "saikei."

# Panel patterns  
'SAIKEI_PT_' → 'SAIKEI_PT_'
'SAIKEI_MT_' → 'SAIKEI_MT_'
'SAIKEI_OT_' → 'SAIKEI_OT_'
```

---

## Part 5: Risk Mitigation

### Potential Issues & Solutions

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Broken imports | Medium | Run full test suite after changes |
| Blender registration fails | Low | Test in fresh Blender install |
| Lost git history | Very Low | Use rename, not new repo |
| Old links break | Very Low | GitHub auto-redirects |
| User confusion | Low | Clear announcement, redirect notice |

### Rollback Plan

If something goes catastrophically wrong:

```bash
# Restore from backup
cd "C:\Users\amish\OneDrive\OneDrive Documents\GitHub"
rmdir /S /Q Saikei Civil
xcopy /E /I Saikei Civil_backup_20251204 Saikei Civil
```

---

## Part 6: Timeline Recommendation

### Suggested Schedule

| Day | Task | Duration |
|-----|------|----------|
| Day 1 | Secure domains, create GitHub org, social handles | 1 hour |
| Day 1 | Create backup, prepare environment | 30 min |
| Day 2 | Codebase refactoring (all file changes) | 3-4 hours |
| Day 2 | Testing in Blender | 1 hour |
| Day 2 | Repository transfer | 15 min |
| Day 3 | Post-migration cleanup | 1 hour |
| Day 3 | Announcements and communication | 1 hour |

**Total estimated time: 7-8 hours spread over 2-3 days**

---

## Part 7: Post-Migration Verification Checklist

### Functionality Tests

- [ ] Extension installs in Blender
- [ ] All panels appear correctly
- [ ] All operators work
- [ ] IFC files save/load correctly
- [ ] Tests pass
- [ ] No "Saikei Civil" strings in Blender UI

### Repository Tests

- [ ] Old URL redirects to new
- [ ] Clone works: `git clone https://github.com/saikeicivil/saikei`
- [ ] All branches transferred
- [ ] All tags transferred
- [ ] Issues transferred (if any)

### External Tests

- [ ] Website points to new repo
- [ ] Documentation links work
- [ ] Social media links correct

---

## Appendix A: Automated Refactoring Script

Save this as `refactor_to_saikei.py` and run from repository root:

```python
#!/usr/bin/env python3
"""
Automated refactoring script: Saikei Civil → Saikei Civil
Run from repository root AFTER creating backup!
"""

import os
import re
from pathlib import Path

# Replacement mappings (order matters for some)
REPLACEMENTS = [
    # Extension ID (most specific first)
    (r'saikei_civil', 'saikei_civil'),
    
    # Operator idnames
    (r'bl_idname\s*=\s*["\']saikei\.', 'bl_idname = "saikei.'),
    
    # Panel idnames
    (r'SAIKEI_PT_', 'SAIKEI_PT_'),
    (r'SAIKEI_MT_', 'SAIKEI_MT_'),
    (r'SAIKEI_OT_', 'SAIKEI_OT_'),
    
    # Class names
    (r'Saikei Civil(\w+)', r'Saikei\1'),
    
    # Property references
    (r'bpy\.types\.Scene\.saikei', 'bpy.types.Scene.saikei'),
    (r'context\.scene\.saikei', 'context.scene.saikei'),
    
    # General replacements
    (r'Saikei Civil', 'Saikei Civil'),
    (r'saikei', 'saikei'),
    (r'SAIKEI', 'SAIKEI'),
]

EXTENSIONS = {'.py', '.toml', '.md', '.txt', '.rst'}
EXCLUDE_DIRS = {'.git', '__pycache__', '.vscode', 'venv', 'backup'}

def process_file(filepath: Path) -> bool:
    """Process a single file, return True if changes made."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return False
    
    original = content
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True
    return False

def main():
    root = Path('.')
    changed_files = []
    
    for filepath in root.rglob('*'):
        if filepath.is_file():
            # Skip excluded directories
            if any(excluded in filepath.parts for excluded in EXCLUDE_DIRS):
                continue
            
            # Only process known extensions
            if filepath.suffix.lower() in EXTENSIONS:
                if process_file(filepath):
                    changed_files.append(filepath)
                    print(f"✓ Updated: {filepath}")
    
    print(f"\n{'='*50}")
    print(f"Total files updated: {len(changed_files)}")
    print(f"{'='*50}")
    
    if changed_files:
        print("\nNext steps:")
        print("1. Review changes with: git diff")
        print("2. Rename folder: git mv saikei saikei")
        print("3. Test in Blender")
        print("4. Commit: git commit -am 'Rebrand to Saikei Civil'")

if __name__ == '__main__':
    main()
```

---

## Appendix B: Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│           SAIKEI CIVIL MIGRATION QUICK REF              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  OLD                    →    NEW                        │
│  ───                         ───                        │
│  Saikei Civil           →    Saikei Civil               │
│  saikei           →    saikei                     │
│  SAIKEI           →    SAIKEI                     │
│  saikei_civil       →    saikei_civil               │
│  saikei.operator  →    saikei.operator            │
│  SAIKEI_PT_       →    SAIKEI_PT_                 │
│                                                         │
│  GITHUB                                                 │
│  ──────                                                 │
│  Org:  github.com/saikeicivil                          │
│  Repo: github.com/saikeicivil/saikei                   │
│                                                         │
│  DOMAINS                                                │
│  ───────                                                │
│  Primary:   saikeicivil.org                            │
│  Secondary: saikeicivil.com                            │
│                                                         │
│  SOCIAL                                                 │
│  ──────                                                 │
│  All platforms: @saikeicivil                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

**Document Version:** 1.0  
**Created:** December 4, 2025  
**Status:** Ready for Review

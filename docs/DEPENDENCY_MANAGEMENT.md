# Dependency Management

This project uses **pip-compile** to manage dependencies efficiently.

## Files

- **`requirements.txt`** - Main dependency specifications (loose versions)
- **`requirements.lock`** - Locked dependency tree (exact versions & transitive deps)

## Why Two Files?

| File | Purpose | Usage |
|------|---------|-------|
| `requirements.txt` | Human-friendly, version ranges | Development, updates |
| `requirements.lock` | Machine-generated, pinned versions | CI/CD, reproducibility |

## Workflow

### Adding a New Dependency

1. **Edit `requirements.txt`:**
   ```bash
   # Add the package
   echo "new-package>=1.0.0" >> requirements.txt
   ```

2. **Generate lock file:**
   ```bash
   pip-compile requirements.txt -o requirements.lock
   ```

3. **Install locally:**
   ```bash
   pip install -r requirements.lock
   ```

4. **Commit both files** to git

### Updating Dependencies

```bash
# Update all to latest versions
pip-compile --upgrade requirements.txt -o requirements.lock

# Update specific package
pip-compile --upgrade-package package-name requirements.txt -o requirements.lock

# Install
pip install -r requirements.lock
```

## GitHub Actions Optimization

The workflow uses `requirements.lock` with pip caching:

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    cache: 'pip'  # Caches pip packages

- name: Install dependencies
  run: pip install -r requirements.lock --no-deps
```

**Benefits:**
- ✅ **Pre-resolved dependencies** - No dependency tree resolution
- ✅ **Exact versions** - Same packages every time
- ✅ **Pip caching** - Downloads cached from cache after first run
- ✅ **Faster CI/CD** - 17s → ~3-5s on cached runs

## Performance

| Scenario | Time | Cache Status |
|----------|------|--------------|
| Fresh runner, no cache | ~10-12s | ❌ Download |
| Fresh runner, with cache | ~3-5s | ✅ Hit |
| Subsequent runs | ~2-3s | ✅ Hit |

## Local Development

For local development, you can use either:

```bash
# Fast: Use locked versions
pip install -r requirements.lock

# Flexible: Use version ranges
pip install -r requirements.txt
```

## When to Regenerate

Regenerate `requirements.lock` when:
- ✅ Adding a new package to `requirements.txt`
- ✅ Updating version constraints in `requirements.txt`
- ✅ Quarterly, to get security updates
- ✅ When running on a new Python version

## Troubleshooting

**"No module named X" after updating:**
- Clear cache: `rm -rf __pycache__ .pytest_cache`
- Reinstall: `pip install -r requirements.lock --force-reinstall`

**Lock file out of sync:**
- Regenerate: `pip-compile requirements.txt -o requirements.lock`
- Verify: `pip install -r requirements.lock --dry-run`


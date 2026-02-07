# GitHub Actions Guide - FPL ETL Pipeline

## 🚀 How to Trigger the Pipeline

The pipeline can be triggered in **4 different ways**:

---

## 1. ⏰ Automatic Schedule (Recommended)

The pipeline runs automatically **every Saturday at 2 AM UTC** during the season.

**No action needed** - just push the YAML file to GitHub and it will run automatically.

### Customize the Schedule

Edit `.github/workflows/etl.yml`:

```yaml
schedule:
  - cron: '0 2 * * 6'  # Every Saturday at 2 AM UTC
```

**Cron Schedule Examples:**
```yaml
# Every day at midnight UTC
- cron: '0 0 * * *'

# Every 6 hours
- cron: '0 */6 * * *'

# Every Monday at 9 AM UTC
- cron: '0 9 * * 1'

# Multiple schedules (Saturday + Wednesday)
schedule:
  - cron: '0 2 * * 6'  # Saturday 2 AM
  - cron: '0 2 * * 3'  # Wednesday 2 AM
```

**Cron Format:**
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
│ │ │ │ │
* * * * *
```

---

## 2. 🖱️ Manual Trigger (GitHub UI)

**Steps:**
1. Go to your GitHub repository
2. Click **"Actions"** tab
3. Click **"FPL ETL Pipeline (Medallion)"** workflow
4. Click **"Run workflow"** button (top right)
5. Select branch (usually `main`)
6. Click **"Run workflow"**

**When to use:**
- Testing the pipeline
- Running outside the schedule
- Immediate data refresh needed

---

## 3. 🔄 Automatic on Push

The pipeline runs automatically when you push to the `main` branch.

```bash
git add .
git commit -m "Update configuration"
git push origin main
```

**When to use:**
- After making code changes
- After updating configuration
- During development

**To disable**, edit `.github/workflows/etl.yml` and remove:
```yaml
on:
  push:
    branches:
      - main
```

---

## 4. 🌐 API Trigger (External)

Trigger the pipeline from external services or scripts using GitHub API.

### Using GitHub CLI

```bash
# Install GitHub CLI
# https://cli.github.com/

# Trigger the workflow
gh workflow run "FPL ETL Pipeline (Medallion)" \
  --repo yourusername/FPL-ETL
```

### Using cURL

```bash
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/FPL-ETL/actions/workflows/etl.yml/dispatches \
  -d '{"ref":"main"}'
```

### Using Python

```python
import requests

headers = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': 'token YOUR_GITHUB_TOKEN'
}

response = requests.post(
    'https://api.github.com/repos/OWNER/FPL-ETL/actions/workflows/etl.yml/dispatches',
    headers=headers,
    json={'ref': 'main'}
)

print(f"Status: {response.status_code}")
```

**When to use:**
- Integration with other systems
- Custom scheduling logic
- Webhook triggers

---

## 📋 Setup Checklist

Before the pipeline can run, you need to configure secrets:

### 1. Set Up GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add these secrets:

| Secret Name | Value | Where to Get |
|-------------|-------|--------------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_KEY` | `eyJxxx...` | Supabase → Project Settings → API → service_role key |

⚠️ **Important**: Use the **service_role** key, NOT the anon key!

### 2. Verify YAML File

Make sure `.github/workflows/etl.yml` exists in your repository:

```bash
git add .github/workflows/etl.yml
git commit -m "Add GitHub Actions workflow"
git push origin main
```

### 3. Enable Actions

1. Go to **Settings** → **Actions** → **General**
2. Under "Actions permissions", select **"Allow all actions and reusable workflows"**
3. Click **Save**

---

## 📊 Monitoring Pipeline Runs

### View Run History

1. Go to **Actions** tab
2. Click on workflow name
3. See all runs with status (✅ success, ❌ failed, 🟡 in progress)

### View Run Details

1. Click on any run
2. Click on **"etl_job"**
3. Expand steps to see logs:
   - Checkout repository
   - Set up Python
   - Install dependencies
   - **Run Medallion ETL Pipeline** ← Main logs here

### Download Logs (if failed)

Failed runs automatically save logs as artifacts:

1. Go to failed run
2. Scroll to **"Artifacts"** section
3. Download `etl-logs` (retained for 7 days)

---

## ⚙️ Customizing the Pipeline

### Change Python Version

Edit `.github/workflows/etl.yml`:

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: "3.12"  # Change version here
```

### Add Notifications

Add email notifications on failure:

```yaml
- name: Send email on failure
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: FPL ETL Pipeline Failed
    body: Pipeline failed. Check logs at ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
    to: your-email@example.com
    from: FPL ETL Bot
```

### Add Slack Notifications

```yaml
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'FPL ETL Pipeline completed'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Run Only on Specific Files

```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'src/**'
      - 'requirements.txt'
      - '.github/workflows/etl.yml'
```

---

## 🐛 Troubleshooting

### Pipeline Not Running

**Check:**
1. ✅ Secrets are set correctly (SUPABASE_URL, SUPABASE_SERVICE_KEY)
2. ✅ Actions are enabled in repository settings
3. ✅ YAML file is in `.github/workflows/` directory
4. ✅ YAML syntax is valid (use YAML linter)
5. ✅ Branch name matches (usually `main`, not `master`)

### Pipeline Failing

**Common issues:**

1. **Missing secrets**
   ```
   Error: SUPABASE_URL not set
   ```
   → Add secrets in GitHub Settings

2. **Wrong Supabase key**
   ```
   Error: 401 Unauthorized
   ```
   → Use service_role key, not anon key

3. **Dependencies failed**
   ```
   Error: No matching distribution found
   ```
   → Check requirements.txt for invalid packages

4. **Import errors**
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   → Verify project structure and imports

### View Detailed Logs

Enable debug logging:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add variable: `ACTIONS_STEP_DEBUG` = `true`
3. Re-run the workflow

---

## 📅 Recommended Schedule

### During FPL Season

**Option 1: Twice a week** (recommended)
```yaml
schedule:
  - cron: '0 2 * * 3'  # Wednesday 2 AM UTC (after midweek games)
  - cron: '0 2 * * 6'  # Saturday 2 AM UTC (after weekend games)
```

**Option 2: After each gameweek** (manual)
- Use manual trigger after gameweek ends

**Option 3: Daily** (aggressive)
```yaml
schedule:
  - cron: '0 3 * * *'  # Every day at 3 AM UTC
```

### Off-Season

**Disable scheduled runs:**
- Comment out the schedule section
- Keep manual trigger available

```yaml
on:
  workflow_dispatch:  # Manual only
  # schedule:
  #   - cron: '0 2 * * 6'  # Disabled
```

---

## 🔐 Security Best Practices

1. ✅ **Never commit secrets** to the repository
2. ✅ **Use service_role key** only in GitHub Secrets (not in code)
3. ✅ **Rotate keys** periodically
4. ✅ **Limit secret access** to necessary people
5. ✅ **Review workflow logs** for exposed data
6. ✅ **Use HTTPS** for all API calls

---

## 📖 Examples

### Weekly Saturday Refresh

```yaml
on:
  schedule:
    - cron: '0 2 * * 6'  # Saturday 2 AM UTC
  workflow_dispatch:
```

### After Every Code Push

```yaml
on:
  push:
    branches:
      - main
  workflow_dispatch:
```

### Manual Only

```yaml
on:
  workflow_dispatch:
```

### Multiple Schedules

```yaml
on:
  schedule:
    - cron: '0 2 * * 3'  # Wednesday
    - cron: '0 2 * * 6'  # Saturday
  workflow_dispatch:
  push:
    branches:
      - main
```

---

## 🎯 Quick Start

**To get started right now:**

1. **Set secrets** (GitHub Settings → Secrets)
   - SUPABASE_URL
   - SUPABASE_SERVICE_KEY

2. **Push YAML file**
   ```bash
   git add .github/workflows/etl.yml
   git commit -m "Add GitHub Actions workflow"
   git push origin main
   ```

3. **Test manual trigger**
   - Go to Actions → Run workflow

4. **Wait for scheduled run**
   - Next Saturday 2 AM UTC (or customize schedule)

---

## 📞 Need Help?

- Check [README.md](../README.md) for pipeline details
- Review [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) for full documentation
- Open GitHub issue for support

---

**Next Steps:**
1. Set up GitHub Secrets
2. Customize schedule (if needed)
3. Test manual trigger
4. Monitor first run

**Happy automating! 🚀**

# FPL-ETL Documentation Index

**Version**: 2.0.0  
**Last Updated**: February 7, 2026

---

## 📚 Documentation Structure

### Essential Reading (Start Here)

1. **[README.md](../README.md)** ⭐  
   Main project overview, quick start, and basic usage

2. **[fpl_etl_visualization.html](fpl_etl_visualization.html)** 🎨  
   Interactive visual guide (open in browser) - **Best for understanding the system**

3. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** ⚡  
   Quick commands and common queries

---

### Architecture & Design

4. **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** 📖  
   Comprehensive guide with all details, examples, and API reference

5. **[MEDALLION_ARCHITECTURE.md](MEDALLION_ARCHITECTURE.md)** 🥉🥈🥇  
   Bronze, Silver, Gold layers explained

6. **[DIMENSIONAL_MODEL.md](DIMENSIONAL_MODEL.md)** 📊  
   Star schema design and relationships

7. **[er_diagram.md](er_diagram.md)** 🔗  
   Entity-relationship diagram (Mermaid format)

---

### Migration & Updates

8. **[INCREMENTAL_MODE_GUIDE.md](INCREMENTAL_MODE_GUIDE.md)** 🔄 **NEW!**  
   Full load vs incremental mode explained - **Read this after first run!**

9. **[MEDALLION_MIGRATION.md](MEDALLION_MIGRATION.md)** 🔄  
   How to migrate from old flat structure (if upgrading)

10. **[UPDATED_DIMENSIONAL_MODEL.md](UPDATED_DIMENSIONAL_MODEL.md)** ✨  
    Latest enhancements (fixtures, complete player data)

11. **[GITHUB_ACTIONS_GUIDE.md](GITHUB_ACTIONS_GUIDE.md)** 🤖 **NEW!**  
    Automation guide - scheduled runs, manual triggers, setup

---

### Technical Reference

10. **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** 📁  
    Detailed folder and file structure

11. **[DEPENDENCY_MANAGEMENT.md](DEPENDENCY_MANAGEMENT.md)** 📦  
    Managing Python dependencies

12. **[INCREMENTAL_MODE_GUIDE.md](INCREMENTAL_MODE_GUIDE.md)** ⚙️  
    Full load vs incremental configuration

---

## 🎯 Quick Navigation

### I want to...

| Task | Document |
|------|----------|
| **Understand the system visually** | [fpl_etl_visualization.html](fpl_etl_visualization.html) |
| **Get started quickly** | [README.md](../README.md) → Quick Start section |
| **Switch to incremental mode** | [INCREMENTAL_MODE_GUIDE.md](INCREMENTAL_MODE_GUIDE.md) ⭐ |
| **Set up automation** | [GITHUB_ACTIONS_GUIDE.md](GITHUB_ACTIONS_GUIDE.md) |
| **Learn about the architecture** | [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → Architecture section |
| **Query data** | [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → Usage Examples |
| **Understand star schema** | [DIMENSIONAL_MODEL.md](DIMENSIONAL_MODEL.md) |
| **See all relationships** | [er_diagram.md](er_diagram.md) |
| **Deploy to production** | [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → Deployment section |
| **Troubleshoot issues** | [README.md](../README.md) → Troubleshooting section |

---

## 📊 Data Model Quick Reference

### Dimensions (5 Tables)
- `dim_clubs` - Premier League teams
- `dim_players` - Players with 70+ columns
- `dim_managers` - FPL managers
- `dim_gameweeks` - Gameweek calendar
- `dim_fixtures` - Matches with difficulty ratings

### Facts (4 Tables)
- `fact_player_performance` - Gameweek stats
- `fact_player_seasonal_stats` - Season totals
- `fact_manager_picks` - Manager selections
- `manager_gameweek_performance` - Denormalized view

---

## 🏗️ Architecture Quick Reference

### Medallion Layers
```
🥉 Bronze  → Raw JSON (incremental: last 2 GWs)
🥈 Silver  → Cleaned CSV/Parquet
🥇 Gold    → Star schema (5 dims + 4 facts)
```

### Pipeline Command
```bash
python -m src.main_medallion
```

---

## 📖 Complete Documentation Map

```
docs/
├── INDEX.md                          ← You are here
│
├── Essential/
│   ├── README.md                     → Overview & quick start
│   ├── fpl_etl_visualization.html    → Interactive guide ⭐
│   └── QUICK_REFERENCE.md            → Quick commands
│
├── Architecture/
│   ├── COMPLETE_GUIDE.md             → Full guide with examples
│   ├── MEDALLION_ARCHITECTURE.md     → Layer design
│   ├── DIMENSIONAL_MODEL.md          → Star schema
│   └── er_diagram.md                 → ER diagram
│
├── Migration/
│   ├── MEDALLION_MIGRATION.md        → Upgrade guide
│   └── UPDATED_DIMENSIONAL_MODEL.md  → Latest changes
│
└── Technical/
    ├── PROJECT_STRUCTURE.md          → File structure
    └── DEPENDENCY_MANAGEMENT.md      → Dependencies
```

---

## 🎨 Best Way to Explore

### For Visual Learners
1. Open `fpl_etl_visualization.html` in browser
2. Navigate through the 6 tabs
3. See diagrams, examples, and usage

### For Code-First Learners
1. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
2. Run pipeline: `python -m src.main_medallion`
3. Query data using examples from [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)

### For Architects/Data Engineers
1. Read [MEDALLION_ARCHITECTURE.md](MEDALLION_ARCHITECTURE.md)
2. Study [DIMENSIONAL_MODEL.md](DIMENSIONAL_MODEL.md)
3. Review [er_diagram.md](er_diagram.md)

---

## 🚀 Common Workflows

### Development
```bash
# 1. Read QUICK_REFERENCE.md
# 2. Run pipeline
python -m src.main_medallion
# 3. Query data (see COMPLETE_GUIDE.md examples)
```

### Production Deployment
```bash
# 1. Read COMPLETE_GUIDE.md → Deployment section
# 2. Set up GitHub Actions
# 3. Configure Supabase
# 4. Test pipeline
```

### Understanding Changes
```bash
# 1. Check UPDATED_DIMENSIONAL_MODEL.md
# 2. Review ER diagram: er_diagram.md
# 3. See visual: fpl_etl_visualization.html
```

---

## 📞 Support

**Questions?**
1. Check [README.md](../README.md) → Troubleshooting
2. Review [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → FAQ
3. Open issue on GitHub

---

**Start Here**: [fpl_etl_visualization.html](fpl_etl_visualization.html) (open in browser) 🎨

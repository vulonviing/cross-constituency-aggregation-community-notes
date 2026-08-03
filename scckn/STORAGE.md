# Data Storage

## Quota Check

```bash
/software/bin/quota    # Shows current disk usage
```

---

## Directories and Quotas

| Directory | Shortcut | Size | Quota | Backup | Usage |
|-----------|----------|------|-------|--------|-------|
| `/home/scc/emrecan.ulu` | `$HOME` | 11 TB total | **100 GB** | Daily | Settings, code |
| `/work` | `/work` | 640 TB | None | Monthly | Active data |
| `/localscratch` | `/scratch` | 1–3 TB/node | None | **None** | Temporary files |

**Important:** Do not put large data in the home directory. Use `/work` for computation.

---

## File Transfer

Always use `rsync` (not `cp` or `mv`) to transfer data to/from the cluster.

```bash
# Mac → Cluster
rsync -avhSPz emrecan.ulu@scc.uni-konstanz.de:/work/emrecan.ulu/ ./local/

# Cluster → Mac
rsync -avhSPz ./local/ emrecan.ulu@scc.uni-konstanz.de:/work/emrecan.ulu/
```

For fast connections (above 1 GB/s):
```bash
rsync -avhSP -e "ssh -T -c aes128-ctr -o Compression=no -x" host:source/ dest/
```

---

## Backup Policy

- **Home directory:** Daily backup + 15-minute snapshots
- **/work:** Monthly backup
- **/localscratch:** **No backup** — for temporary job files only

To recover a file from backup, contact Stefan.

---

## Account Deletion

Notify Stefan when you stop using the cluster. Otherwise:
- 5 years inactive → account deleted
- Data archived for at least 10 years

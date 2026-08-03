# Useful Tricks

## Checkpointing (For Long Jobs)

Use checkpointing for long-running simulations — if the connection drops or the system fails, you can resume from where you left off.

```bash
dmtcp_checkpoint -b -i 21600 -c checkpoint_dir/ python script.py
```

- `-i 21600` → Writes a checkpoint every 6 hours
- `-b` → Coordinator runs on the same CPU
- `-c` → Directory where checkpoint files are written

To resume:
```bash
./checkpoint_dir/dmtcp_restart_script.sh
```

**Note:** Only serial and OpenMP jobs are supported. Does not work with MPI jobs.

---

## Module Commands

```bash
module load conda                  # Load Anaconda
source activate python-3.13        # Activate the Python environment
module list                        # Show loaded modules
module purge                       # Remove all modules
module avail numlib                # See what is available in a specific category
module whatis mkl                  # Brief description of a module
```

To make persistent, add to `~/.bashrc`:
```bash
module load conda
source activate python-3.13
```

---

## Adding Your Own Environment to JupyterHub

```bash
module load conda
source activate python-3.13
python -m ipykernel install --user --name python-3.13 --display-name "Python (3.13)"
```

It will appear in JupyterHub as the "Python (3.13)" kernel.

---

## Interactive Session

For long terminal tasks, connect directly to a node:
```bash
qlogin -q scc
```

---

## Check Resource Usage After a Job

```bash
qacct -j <jobid>
```

Shows how much RAM and time were actually used. Adjust subsequent jobs accordingly — requesting too much increases queue wait time.

---

## File Compression

Compress large data before storing to preserve disk quota:

```bash
# Fast and good compression
plzip -9 file.dat              # Single file
tar --lzip -cf archive.tar.lz data/  # Directory

# Best compression (slow)
zpaq -m 5 a archive.zpaq data/
```

gzip and zip compress relatively weakly; prefer plzip for large data.

# Instructions for Claude

## What Is This Project?

This directory contains the setup steps for connecting to and using the SCCKN (Scientific Compute Cluster) at the University of Konstanz. The user uses this cluster for research purposes: uploading and downloading files, submitting jobs, and working through Jupyter.

---

## How to Update SCCKN_SETUP.md

`SCCKN_SETUP.md` must be updated after every new setup step, configuration change, or newly learned command.

### Update Rules

- Update the relevant section each time a new step is completed
- If a new topic is added (e.g., job scheduler, Python environment setup), open a new numbered section
- Remove outdated or no-longer-applicable information; keep the file clean
- Always show commands inside code blocks
- Keep the Quick Reference section up to date with the most frequently used commands

---

## Language and Style

### Write in English

All explanations must be in English. Commands and technical terms (ssh, mount, tmux, etc.) remain as-is.

### Keep It Simple

- Use short sentences
- Explain jargon ("kernel extension = low-level software added to the system kernel")
- Write step by step; each step should describe exactly one action
- State the reason in one sentence ("SSH key created → so you don't have to type a password on every login")

### Tables and Code Blocks

- Account details and fixed values in table format
- All commands inside ``` code blocks ```
- Prefer short bullet lists over long prose explanations

---

## General Behavioral Rules

- When the user asks about technical details, explain briefly and clearly
- If asked whether something is safe, research it first, then answer
- Present setup steps in a sequential and testable manner
- Update the documentation when a step is completed; do not leave it half-finished
- Do not suggest extra features or installations — do only what the user asks for

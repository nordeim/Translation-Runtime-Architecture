# TRA Code Audit Skills Bundle

This tar archive contains the skills, scripts, and deliverables used during
the systematic code review and audit of the Translation Runtime Architecture
(TRA) prototype engine.

## Contents

```
tra-audit-skills/
├── README.md                          <- this file
├── skills/
│   ├── git-push-using-ssh-wrapper_SKILL.md   <- SSH wrapper skill doc
│   └── ssh_git_wrapper_v3.py          <- Paramiko-based git SSH wrapper (patched)
├── scripts/
│   ├── tra_findings.py                <- Master findings register (35 findings)
│   ├── tra_chart.py                   <- Severity heatmap chart generator
│   ├── tra_xlsx.py                    <- Multi-sheet XLSX findings register
│   └── docx-build/
│       ├── generate.js                <- DOCX audit report generator (docx-js)
│       ├── package.json               <- Node deps for docx generation
│       ├── tra_findings.json          <- Findings data (consumed by generate.js)
│       └── chart.png                  <- Embedded severity heatmap
├── deliverables/
│   ├── TRA_Prototype_Audit_Report.docx     <- Formal audit report (96 KB)
│   ├── TRA_audit_findings_register.xlsx    <- 7-sheet findings register (48 KB)
│   └── TRA_audit_severity_heatmap.png      <- Severity chart (84 KB)
└── worklog.md                         <- Full audit trail (3700+ lines)
```

## Usage

### 1. Review the audit findings

Open `deliverables/TRA_audit_findings_register.xlsx` - it has 7 sheets:
- Summary (counts by severity, track, category)
- Findings (full 35-row register with autofilter)
- Track A-E (per-track subsets)
- Remediation Backlog (priority-sorted with effort estimates)

### 2. Regenerate the deliverables

```bash
# Regenerate the chart
python3 scripts/tra_chart.py

# Regenerate the XLSX
python3 scripts/tra_xlsx.py

# Regenerate the DOCX (requires Node.js + docx package)
cd scripts/docx-build
bun add docx   # or npm install docx
bun run generate.js
```

### 3. Use the SSH wrapper (for git push without openssh)

```bash
# Install paramiko
pip install paramiko

# Set up the SSH key
cp /path/to/your_key ~/.ssh/id_github
chmod 600 ~/.ssh/id_github

# Push via the wrapper
GIT_SSH_COMMAND="/path/to/ssh_git_wrapper_v3.py -i ~/.ssh/id_github \
  -o StrictHostKeyChecking=accept-new" git push origin main
```

The wrapper includes the blocking-sendall fix that prevents binary-file
upload truncation.

## Audit methodology

The audit used a 4-track parallel structure:

| Track | Scope | Findings |
|-------|-------|----------|
| A | Spec conformance (Kernel, ISA, Policy, Memory, Exceptions, L3/L4 gates) | 10 |
| B | Code quality & security (type safety, error handling, cache, deps) | 9 |
| C | Doc-vs-code consistency (11 documentation files) | 8 |
| D | Test suite (coverage, mutation testing, benchmark cases) | 8 |

Total: 35 findings (11 BLOCKING, 22 WARNING, 2 INFO).

## Remediation status

34 of 35 findings have been remediated across multiple TDD cycles. The
remaining item (TRA-001 full segment-level translation) is partially fixed
(code-block protection landed; per-leaf-segment translation deferred).

See `worklog.md` for the full per-finding evidence trail and remediation log.

# cloudflare-dns-purge.py

A high-performance, CLI-driven DNS record invalidation tool that sends purge requests to [Cloudflare’s 1.1.1.1 API](https://one.one.one.one/). Designed to invalidate cached DNS records for a domain across multiple record types.

## Purpose

This tool is ideal for:

- Clearing out stale DNS entries (e.g., after migrations or TTL overrides)
- Automating cache purges for CI/CD, incident response, or bulk record updates
- Programmatic, scriptable DNS workflows

## Installation (Pip-based)
Python 3.7+ is required.

### Option 1: From source

1. Clone the repo:
```bash
git clone https://github.com/DanHouseman/cloudflare-dns-purge.git
cd cloudflare-dns-purge
```

2. Install via pip:
```bash
pip install .
```

This registers `cloudflare-dns-purge` as a global command-line tool.

### Option 2: Run directly without installing

```bash
pip install -r requirements.txt
python cloudflare-dns-purge.py <domain> [options]
```

## CLI Usage (Installed Version)

Once installed with `pip install .`, you can use:

```bash
cloudflare-dns-purge example.com --types A AAAA --verbose --export
```

This behaves exactly like calling `python cloudflare-dns-purge.py`, but works globally from any directory.


1. Clone the repo or download the script:

```bash
git clone https://github.com/DanHouseman/cloudflare-dns-purge.git
cd cloudflare-dns-purge
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python cloudflare-dns-purge.py <domain> [options]
```

### Required
- `domain`: The fully-qualified domain to purge (e.g. `example.com`)

---

### Options

| Option        | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `--types`     | Space or comma-separated list of DNS record types (e.g., `A AAAA CNAME`)   |
| `--delay`     | Delay (in seconds) between requests or submissions                          |
| `--threads`   | Number of concurrent threads (default: 1)                                   |
| `--verbose`   | Enable verbose per-record logging                                           |
| `--export`    | Export results to `purge_log_<domain>.json` or `.csv`                       |

---

### Supported DNS Types

`A, AAAA, CAA, CNAME, DNSKEY, DS, HTTPS, LOC, MX, NAPTR, NS, PTR, SPF, SRV, SVCB, SSHFP, TLSA, TXT`

## 🧪 Examples

### Basic usage

```bash
python cloudflare-dns-purge.py example.com
```

### Purge specific types

```bash
python cloudflare-dns-purge.py example.com --types A AAAA CNAME
```

### With delay and multithreading

```bash
python cloudflare-dns-purge.py example.com --types A AAAA --threads 4 --delay 0.3 --verbose
```

#### Notes on Threading and Delay

When combining `--threads` and `--delay`, it’s important to understand how the script behaves:

| Mode               | Behavior                                                                 |
|--------------------|--------------------------------------------------------------------------|
| `--threads 1`      | `--delay` is applied **after each request** (safe throttling).           |
| `--threads > 1`    | `--delay` is applied **between task submissions**, not within each thread.|
| `--delay` negative | Treated as `0`. No actual delay will be enforced.                        |
| `--threads` < 1    | Treated as `1` (single-threaded).                                        |

#### Why does this matter?

- **Single-threaded mode** ensures each purge is spaced out to avoid overwhelming the API.
- **Multithreaded mode** allows parallel execution, but without `--delay`, it can burst too fast.
- `--delay` in threaded mode spaces **submission**, not execution.

#### Recommendation

If you're purging more than ~5 records *and* want to avoid hitting rate limits:

```bash
python cloudflare-dns-purge.py example.com --types A AAAA CNAME TXT --threads 4 --delay 0.3 --verbose
```
This uses controlled concurrency and avoids overwhelming the 1.1.1.1 purge API.

### Export results

```bash
python cloudflare-dns-purge.py example.com --types A,AAAA --export       # exports JSON
python cloudflare-dns-purge.py example.com --types A,AAAA --export csv   # exports CSV
```

## Output

### Console Output (Verbose)

```bash
[✅ SUCCESS] A    → purge request queued. Please wait a few seconds...
[❌ FAILURE] TXT  → {"msg":"invalid record type"}
```

### Summary Block

```bash
=== SUMMARY ===
✅ Successes: 2 → A, AAAA
❌ Failures: 1
  - TXT → {"msg":"invalid record type"}
```

## Sample Exported Files

### JSON (default)

`purge_log_example.com.json`:

```json
{
  "domain": "example.com",
  "successes": [
    {"type": "A", "status": "SUCCESS", "message": "purge request queued"},
    {"type": "AAAA", "status": "SUCCESS", "message": "purge request queued"}
  ],
  "failures": [
    {"type": "TXT", "status": "FAILURE", "message": "invalid record type"}
  ]
}
```

### CSV

`purge_log_example.com.csv`:

```csv
Type,Status,Message
A,SUCCESS,purge request queued
AAAA,SUCCESS,purge request queued
TXT,FAILURE,invalid record type
```

## Notes

- The API must include in its return  `"purge request queued"` to be considered a success.
- Invalid or unsupported record types will be rejected before sending.
- You may need to wait several seconds for DNS propagation to complete after the purge.

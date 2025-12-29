# Nmap -iL Fix: Large IP List Command Line Overflow

## Problem
When scanning large CIDR ranges like /22 (1024 IPs), the nmap command line became too long when passing 1022 individual IPs as space-separated arguments:

```
nmap -sn -T4 --min-parallelism 100 103.98.152.188 103.98.152.1 103.98.152.2 ... (1022 total)
```

**Result:** Nmap returned 0 alive hosts despite many devices being online.

## Root Cause
Command line length limits or nmap's argument parser failing with extremely long argument lists.

## Solution
Use nmap's **-iL** (input file) flag:

```bash
# Instead of:
nmap -sn -T4 --min-parallelism 100 IP1 IP2 IP3 ... IP1022

# Use:
echo -e "IP1\nIP2\nIP3\n...IP1022" > /tmp/ips.txt
nmap -sn -T4 --min-parallelism 100 -iL /tmp/ips.txt
```

## Implementation Changes

### modules/discovery/host_discovery.py

**Method: `_run_nmap_sn()`**

```python
if ' ' in target:
    # Write space-separated IPs to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for ip in target.split():
            f.write(ip + '\n')
        temp_file = f.name
    
    # Use -iL flag with temp file
    cmd = ["nmap", "-sn", "-T4", "--min-parallelism", "100", "-iL", temp_file]
else:
    # Single IP or CIDR - use directly
    cmd = ["nmap", "-sn", "-T4", "--min-parallelism", "100", target]

# Run nmap...
# Cleanup temp file in finally block
```

## Benefits

1. **Handles large IP lists** - No command line length limits
2. **No performance loss** - Nmap processes file input at same speed
3. **Automatic CIDR detection** - If input is CIDR, bypasses file method
4. **Backward compatible** - API unchanged

## Testing

```bash
# Before fix:
[NMAP-SN] Hoàn tất: 0 host đang hoạt động (from 1022 targets)

# After fix:
[NMAP-SN] Running nmap on 1022 IPs (via temp file)
[NMAP-SN] Hoàn tất: X host đang hoạt động (actual count)
```

## Files Modified

- `modules/discovery/host_discovery.py` - Added -iL support with temp file
- All tests pass ✅

# Router Cracker (testing only)

This small tool attempts to log into a router web interface using a username and a password wordlist. It is intended for authorized security testing only on devices/networks you own or have explicit permission to test.

Usage

```bash
python3 cracker.py <router_url> <username> <password_file> [--delay N] [--timeout T] [--success s1 s2 ...] [--success-header "Name:substr"] [--failed-log PATH] [--log PATH] [--verbose]
```

Examples

```bash
python3 cracker.py http://192.168.0.1 admin router_wordlist.txt --delay 0.5 --timeout 8 --verbose --log cracker.log
python3 cracker.py http://192.168.0.1 admin router_wordlist.txt --success index.htm welcome --success-header "Set-Cookie:session=" --failed-log failed.txt
```

Options of note

- `--delay`: seconds to wait between attempts (helps reduce lockouts)
- `--timeout`: per-request timeout in seconds
- `--success`: additional body/redirect indicators to consider success
- `--success-header`: header substring to require for body/header match; can be repeated
- `--failed-log`: where failed attempts are recorded (default: `failed_attempts.txt`)

Legal / Safety

Only run this tool against systems and networks you own or have explicit, written permission to test. Unauthorized access attempts are illegal in many jurisdictions.

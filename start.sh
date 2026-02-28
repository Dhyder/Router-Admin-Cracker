#!/usr/bin/env bash
# Ensure we run under bash (some systems invoke scripts with other shells by default).
if [ -z "$BASH_VERSION" ]; then
  if command -v bash >/dev/null 2>&1; then
    exec bash "$0" "$@"
  else
    printf "This script requires bash. Please install bash or run on a system with bash.\n" >&2
    exit 1
  fi
fi
# Interactive launcher for cracker.py
# Prompts for router URL (attempts auto-detect), username, wordlist and options

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

echo "${BLUE}Welcome to Router Cracker — the polite and patient kind.${RESET}"
echo "I'll try to sniff your default gateway, then we'll ask a couple of friendly questions (or accept CLI args)."

# Default values
default_wordlist="router_wordlist.txt"
router_url=""
username="admin"
password_file="$default_wordlist"
delay=0.0
timeout=10.0
failed_log="failed_attempts.txt"
log_file=""
verbose=0
auto=0
nonint=0

# Simple arg parsing for long options
while [[ $# -gt 0 ]]; do
  case $1 in
    --router-url)
      router_url=$2; shift 2;;
    --username)
      username=$2; shift 2;;
    --password-file)
      password_file=$2; shift 2;;
    --delay)
      delay=$2; shift 2;;
    --timeout)
      timeout=$2; shift 2;;
    --failed-log)
      failed_log=$2; shift 2;;
    --log)
      log_file=$2; shift 2;;
    --verbose)
      verbose=1; shift;;
    --auto)
      auto=1; shift;;
    --yes|--non-interactive)
      nonint=1; shift;;
    -h|--help)
      echo "Usage: $0 [--router-url URL] [--username USER] [--password-file FILE] [--delay S] [--timeout S] [--failed-log PATH] [--log PATH] [--verbose] [--auto] [--yes]"; exit 0;;
    *)
      echo "Unknown option: $1"; exit 1;;
  esac
done

# Try to auto-detect default gateway if asked or if router_url empty
GW=""
if command -v ip >/dev/null 2>&1; then
  GW=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
fi
if [ -z "$GW" ] && command -v route >/dev/null 2>&1; then
  GW=$(route -n 2>/dev/null | awk '/UG/ {print $2; exit}')
fi
# Extra attempt: ask the kernel what route it would use to reach the public internet
if [ -z "$GW" ] && command -v ip >/dev/null 2>&1; then
  GW=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="via"){print $(i+1); exit}}')
fi

if [ -z "$router_url" ] && [ $auto -eq 1 ] && [ -n "$GW" ]; then
  router_url="http://${GW}"
fi

# Interactive prompts only if not provided and not non-interactive
if [ -z "$router_url" ] && [ $nonint -eq 0 ]; then
  if [ -n "$GW" ]; then
    printf "%sDetected gateway %s — try that?%s\n" "$YELLOW" "$GW" "$RESET"
    printf "Use http://%s as router URL? [Y/n] " "$GW"
    read -r usegw
    if [ "$usegw" = "" ] || [[ "$usegw" =~ ^([yY][eE]?[sS]?)$ ]]; then
      router_url="http://${GW}"
    else
      printf "Enter router URL (eg. http://192.168.0.1): "
      read -r router_url
    fi
  else
    printf "Couldn't detect gateway — enter router URL (eg. http://192.168.0.1): "
    read -r router_url
  fi
fi

if [ -z "$username" ] && [ $nonint -eq 0 ]; then
  printf "Username to try [admin]: "
  read -r username
  username=${username:-admin}
fi

if [ -z "$password_file" ] && [ $nonint -eq 0 ]; then
  printf "Password file [${default_wordlist}]: "
  read -r password_file
  password_file=${password_file:-$default_wordlist}
fi

if [ $nonint -eq 0 ]; then
  printf "Delay between attempts in seconds [${delay}]: "
  read -r input_delay
  delay=${input_delay:-$delay}
  printf "Timeout per request in seconds [${timeout}]: "
  read -r input_timeout
  timeout=${input_timeout:-$timeout}
fi

if [ -z "$router_url" ]; then
  printf "Router URL is required in non-interactive mode. Use --router-url or run interactively.\n"; exit 1
fi

printf "\n%sReady to politely try passwords against %s as %s.%s\n" "$GREEN" "$router_url" "$username" "$RESET"
printf "Failed attempts will be stored in '%s' (use --failed-log to change).\n" "$failed_log"

if [ $nonint -eq 0 ]; then
  printf "Start now? [y/N] "
  read -r startnow
  if [[ ! "$startnow" =~ ^([yY][eE]?[sS]?)$ ]]; then
    echo "Ok, aborted. Coffee first? ☕"; exit 1
  fi
fi

echo "Launching — hold on to your ethernet cable..."
printf "%s" "${YELLOW}"

# Build command
cmd=(python3 cracker.py "$router_url" "$username" "$password_file" --delay "$delay" --timeout "$timeout" --failed-log "$failed_log")
if [ -n "$log_file" ]; then
  cmd+=(--log "$log_file")
fi
if [ $verbose -eq 1 ]; then
  cmd+=(--verbose)
fi

"${cmd[@]}" &
pid=$!

# Gus messages while running
msgs=(
  "I'm Gus — watching the packets so you don't have to."
  "Thinking... correlating vibes with IP addresses."
  "Pro tip: small delays reduce lockouts and drama."
  "Joke: I would tell you a UDP joke but you might not get it."
  "If you remember part of the password, try Combine in the GUI."
)

while kill -0 $pid 2>/dev/null; do
  # print a random Gus line
  idx=$((RANDOM % ${#msgs[@]}))
  echo -e "${YELLOW}Gus: ${msgs[$idx]}${RESET}"
  sleep $((3 + RANDOM % 6))
done

wait $pid
rc=$?
printf "%s" "${RESET}"

if [ $rc -eq 0 ]; then
  echo "${GREEN}🎉 Found a password! Check the output above.${RESET}"
elif [ $rc -eq 2 ]; then
  echo "${YELLOW}No luck this time — try a broader wordlist or a longer delay.${RESET}"
else
  echo "${RED}Something went sideways (exit $rc). Check logs or run with --verbose.${RESET}"
fi

echo "Done. Stay ethical. 👮‍♂️"

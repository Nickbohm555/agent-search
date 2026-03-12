#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="PROMPT_build.md"
AGENTS_FILE="AGENTS.md"
MAX_ITERATIONS=0
REQUIRE_COMMIT_PER_ITERATION="${REQUIRE_COMMIT_PER_ITERATION:-1}"
CODEX_CONTEXT_WINDOW="${CODEX_CONTEXT_WINDOW:-400000}"

if ! [[ "$CODEX_CONTEXT_WINDOW" =~ ^[0-9]+$ ]] || [ "$CODEX_CONTEXT_WINDOW" -le 0 ]; then
  echo "Error: CODEX_CONTEXT_WINDOW must be a positive integer."
  exit 1
fi

is_codex_exec_command() {
  [[ "${AGENT_CMD:-}" == codex\ exec* ]]
}

build_codex_exec_command() {
  local output_last_message_file="$1"
  local cmd="$AGENT_CMD"
  if [[ "$cmd" != *" --json"* ]]; then
    cmd="$cmd --json"
  fi
  if [[ "$cmd" != *" -o "* ]]; then
    cmd="$cmd -o \"$output_last_message_file\""
  fi
  if [[ ! "$cmd" =~ (^|[[:space:]])-($|[[:space:]]) ]]; then
    cmd="$cmd -"
  fi
  printf '%s' "$cmd"
}

print_input_file() {
  local label="$1"
  local path="$2"

  echo "----- BEGIN $label: $path -----"
  cat "$path"
  printf '\n'
  echo "----- END $label: $path -----"
}

print_codex_usage_summary() {
  local iteration="$1"
  local usage_jsonl_file="$2"
  local usage_json
  local input_tokens
  local cached_input_tokens
  local output_tokens
  local total_tokens
  local context_percent

  usage_json="$(jq -c 'select(.type=="turn.completed" and .usage != null) | .usage' "$usage_jsonl_file" | tail -n 1)"
  if [ -z "$usage_json" ]; then
    echo "Codex usage: unavailable"
    return
  fi

  input_tokens="$(printf '%s' "$usage_json" | jq -r '.input_tokens // 0')"
  cached_input_tokens="$(printf '%s' "$usage_json" | jq -r '.cached_input_tokens // 0')"
  output_tokens="$(printf '%s' "$usage_json" | jq -r '.output_tokens // 0')"
  total_tokens=$((input_tokens + output_tokens))
  context_percent="$(awk "BEGIN { printf \"%.2f\", ($total_tokens / $CODEX_CONTEXT_WINDOW) * 100 }")"

  LAST_USAGE_ITERATION="$iteration"
  LAST_USAGE_INPUT_TOKENS="$input_tokens"
  LAST_USAGE_CACHED_INPUT_TOKENS="$cached_input_tokens"
  LAST_USAGE_OUTPUT_TOKENS="$output_tokens"
  LAST_USAGE_TOTAL_TOKENS="$total_tokens"
  LAST_USAGE_CONTEXT_WINDOW="$CODEX_CONTEXT_WINDOW"
  LAST_USAGE_CONTEXT_PERCENT="$context_percent"

  echo "Codex usage: input=$input_tokens cached_input=$cached_input_tokens output=$output_tokens total=$total_tokens"
  echo "Context used: ${context_percent}% of ${CODEX_CONTEXT_WINDOW} tokens"
}

write_codex_usage_markdown() {
  local markdown_file="$1"

  if [ -z "${LAST_USAGE_ITERATION:-}" ]; then
    return
  fi

  cat > "$markdown_file" <<EOF
# Token Usage

- Latest iteration: $LAST_USAGE_ITERATION
- Input tokens: $LAST_USAGE_INPUT_TOKENS
- Cached input tokens: $LAST_USAGE_CACHED_INPUT_TOKENS
- Output tokens: $LAST_USAGE_OUTPUT_TOKENS
- Total tokens: $LAST_USAGE_TOTAL_TOKENS
- Context window: $LAST_USAGE_CONTEXT_WINDOW
- Context used: ${LAST_USAGE_CONTEXT_PERCENT}%
- Last updated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Latest Iteration Formula

\`total_tokens = input_tokens + output_tokens\`
EOF

  echo "Usage markdown: $markdown_file"
}

if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  MAX_ITERATIONS="$1"
elif [ -n "${1:-}" ]; then
  echo "Usage: ./loop.sh [max_iterations]"
  exit 1
fi

if ! [[ "$MAX_ITERATIONS" =~ ^[0-9]+$ ]]; then
  echo "Error: max iterations must be a non-negative integer."
  exit 1
fi

if [ -z "${AGENT_CMD:-}" ]; then
  while :; do
    read -r -p "Which agent are you using? (claude/codex): " AGENT_CHOICE
    AGENT_CHOICE_LOWER="$(printf '%s' "$AGENT_CHOICE" | tr '[:upper:]' '[:lower:]')"
    case "$AGENT_CHOICE_LOWER" in
      claude)
        AGENT_CMD="claude -p"
        break
        ;;
      codex)
        AGENT_CMD="codex exec --sandbox workspace-write -"
        break
        ;;
      *)
        echo "Invalid option. Choose claude or codex."
        ;;
    esac
  done
fi

if [ ! -f "$PROMPT_FILE" ]; then
  echo "Error: prompt file not found: $PROMPT_FILE"
  exit 1
fi

if [ ! -f "$AGENTS_FILE" ]; then
  echo "Error: agents file not found: $AGENTS_FILE"
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Ralph loop must run inside a git repository."
  exit 1
fi

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "Error: working tree is dirty before the loop starts."
  echo "Commit, stash, or discard changes before running Ralph."
  exit 1
fi

ITERATION=0
while :; do
  ITERATION=$((ITERATION + 1))
  START_HEAD="$(git rev-parse --verify HEAD 2>/dev/null || true)"
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  LOOP_STATE_DIR="$REPO_ROOT/.git/ralph-loop"
  LOOP_MSG="$REPO_ROOT/.loop-commit-msg"
  LOOP_FULL="$REPO_ROOT/.loop-commit-msg.full"
  LOOP_USAGE_MARKDOWN="$REPO_ROOT/.planning/token-usage.md"
  LOOP_USAGE_JSONL="$LOOP_STATE_DIR/iteration-$ITERATION.jsonl"
  LOOP_LAST_MESSAGE="$LOOP_STATE_DIR/iteration-$ITERATION.last-message.txt"
  mkdir -p "$LOOP_STATE_DIR"
  rm -f "$LOOP_MSG" "$LOOP_FULL"
  echo "=================================================="
  echo "Ralph loop iteration: $ITERATION"
  echo "Prompt: $PROMPT_FILE"
  echo "Agents: $AGENTS_FILE"
  if is_codex_exec_command; then
    echo "Codex context window: $CODEX_CONTEXT_WINDOW"
  fi
  [ "$MAX_ITERATIONS" -gt 0 ] && echo "Max iterations: $MAX_ITERATIONS"
  echo "=================================================="

  print_input_file "PROMPT" "$PROMPT_FILE"
  print_input_file "AGENTS" "$AGENTS_FILE"

  if is_codex_exec_command; then
    rm -f "$LOOP_USAGE_JSONL" "$LOOP_LAST_MESSAGE"
    cat "$PROMPT_FILE" "$AGENTS_FILE" | eval "$(build_codex_exec_command "$LOOP_LAST_MESSAGE")" | tee "$LOOP_USAGE_JSONL"
    if [ -f "$LOOP_LAST_MESSAGE" ]; then
      cat "$LOOP_LAST_MESSAGE"
      printf '\n'
    fi
    print_codex_usage_summary "$ITERATION" "$LOOP_USAGE_JSONL"
  else
    cat "$PROMPT_FILE" "$AGENTS_FILE" | eval "$AGENT_CMD"
  fi

  END_HEAD="$(git rev-parse --verify HEAD 2>/dev/null || true)"
  if [ "$START_HEAD" != "$END_HEAD" ]; then
    echo "Error: iteration $ITERATION changed git history directly."
    echo "The agent must not create commits. Write .loop-commit-msg and let loop.sh commit."
    exit 1
  fi

  if [ ! -f "$LOOP_MSG" ]; then
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      echo "Error: iteration $ITERATION produced changes but did not write .loop-commit-msg."
      echo "The agent must provide the exact commit subject in .loop-commit-msg."
      exit 1
    fi
  else
    NONEMPTY_LINE_COUNT="$(grep -cve '^[[:space:]]*$' "$LOOP_MSG" || true)"
    if [ "$NONEMPTY_LINE_COUNT" -ne 1 ]; then
      echo "Error: .loop-commit-msg must contain exactly one non-empty line."
      exit 1
    fi

    COMMIT_SUBJECT="$(grep -v '^[[:space:]]*$' "$LOOP_MSG" | head -1 | tr -d '\r')"
    if [ -z "$COMMIT_SUBJECT" ]; then
      echo "Error: .loop-commit-msg is empty."
      exit 1
    fi

    if [[ ! "$COMMIT_SUBJECT" =~ ^[0-9]{2}-[0-9]{2}-task[0-9]+$ && ! "$COMMIT_SUBJECT" =~ ^[0-9]{2}-[0-9]{2}-test[0-9]+$ && ! "$COMMIT_SUBJECT" =~ ^[0-9]{2}-[0-9]{2}-summary$ ]]; then
      echo "Error: .loop-commit-msg does not match the required convention."
      echo "Message: $COMMIT_SUBJECT"
      exit 1
    fi

    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
      echo "Error: .loop-commit-msg exists but there are no file changes to commit."
      exit 1
    fi

    printf '%s\n' "$COMMIT_SUBJECT" > "$LOOP_FULL"
    git add -A
    git commit -F "$LOOP_FULL"
    rm -f "$LOOP_MSG" "$LOOP_FULL"
  fi

  FINAL_HEAD="$(git rev-parse --verify HEAD 2>/dev/null || true)"
  if [ "$REQUIRE_COMMIT_PER_ITERATION" = "1" ] && [ "$START_HEAD" = "$FINAL_HEAD" ]; then
    echo "Error: iteration $ITERATION did not create a commit."
    echo "Write .loop-commit-msg so loop.sh can create the required commit."
    exit 1
  fi

  LAST_SUBJECT="$(git log -1 --pretty=%s 2>/dev/null || true)"
  if [[ ! "$LAST_SUBJECT" =~ ^[0-9]{2}-[0-9]{2}-task[0-9]+$ && ! "$LAST_SUBJECT" =~ ^[0-9]{2}-[0-9]{2}-test[0-9]+$ && ! "$LAST_SUBJECT" =~ ^[0-9]{2}-[0-9]{2}-summary$ ]]; then
    echo "Error: latest commit does not match the required history convention."
    echo "Latest commit: $LAST_SUBJECT"
    exit 1
  fi

  git push -u origin "$(git branch --show-current)"

  if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
    echo "Reached max iterations ($MAX_ITERATIONS)."
    break
  fi
done

if is_codex_exec_command; then
  write_codex_usage_markdown "$LOOP_USAGE_MARKDOWN"
fi

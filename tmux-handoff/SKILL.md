---
name: tmux-handoff
description: Deliver handoff text into an agent CLI running in another tmux pane or window. Use when the user asks to hand off findings, context, or next steps to another tmux window, Codex, Claude Code, or a similar terminal agent.
---

# Tmux Handoff

## Scope

This skill covers only the terminal mechanics of handing off text to another agent running in tmux. The sender owns the handoff content. Do not invent missing findings; only wrap or deliver the provided message.

## Locate the Target

Identify the current tmux session and windows:

```bash
tmux display-message -p '#{session_name}:#{window_index}:#{pane_index}:#{window_name}'
tmux list-windows -F '#{window_index}:#{window_name} #{window_active} #{pane_current_path}'
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_pid} #{pane_current_path} #{pane_title}'
```

If the user names "window 1", prefer target `:<window>.0` or the active pane in that window. Confirm with:

```bash
tmux list-panes -t :1 -F '#{pane_index} #{pane_active} #{pane_pid} #{pane_current_path} #{pane_title}'
tmux capture-pane -t :1 -p -S -40
```

If several panes are plausible, choose the pane whose captured screen shows an agent prompt or recent agent transcript in the expected repository. Ask only if the target remains ambiguous.

## Detect an Agent CLI

Resolve the process tree from the pane tty:

```bash
tty=$(tmux display-message -p -t :1.0 '#{pane_tty}')
ps -o pid,ppid,stat,command -t "$tty"
```

Useful signs: Codex CLI has a `codex` process, often prompt marker `›`, model/status footer, and states like `Working`. Claude Code has a `claude` process and a Claude prompt/status area. Other terminal agents may include `gemini`, `aider`, `opencode`, or a wrapper `node`/`python` whose child command is the agent binary.

Do not paste into a plain shell unless the user explicitly wants a shell command delivered. If only `bash`, `zsh`, or `fish` is running and no agent UI is visible, report that no agent input box is active.

## Confirm the Input Box Is Ready

Before pasting, capture the pane and check that the agent is idle at a prompt:

```bash
tmux capture-pane -t :1.0 -p -S -60
```

Proceed when the bottom of the pane shows a prompt/input area and not an active tool, pager, editor, approval dialog, or long-running command. If the agent is working, wait and recapture instead of interrupting.

Avoid destructive keys such as `C-c`, `C-d`, `Esc`, or editor quit sequences unless the user explicitly asks to interrupt or clear the target.

## Paste the Handoff

Use a tmux buffer to avoid shell quoting problems and preserve multiline text:

```bash
tmp=$(mktemp)
cat > "$tmp" <<'EOF'
HANDOFF TEXT HERE
EOF
tmux load-buffer "$tmp"
tmux paste-buffer -t :1.0
rm "$tmp"
```

If the message is short and one line, `tmux send-keys -t :1.0 -- "text"` is acceptable. For multiline or quoted content, prefer `load-buffer` and `paste-buffer`.

## Submit the Message

After pasting, trigger the target agent with a carriage return:

```bash
tmux send-keys -t :1.0 C-m
```

Use `C-m` first for Codex and as the generic default. In Codex, plain `Enter`, `C-j`, or `M-Enter` can leave pasted multiline content staged in the composer; `C-m` reliably submits the input. For Claude Code and most terminal agents, `C-m` is also equivalent to submitting the prompt.

If `C-m` does not submit, do not keep guessing with interrupt keys. Recapture the pane. If the text is still staged, report that the handoff is pasted but not submitted and include the visible state.

## Verify Delivery

Capture again after a short delay:

```bash
sleep 1
tmux capture-pane -t :1.0 -p -S -60
```

Successful delivery signs include: the pasted text appears in the transcript above the prompt, the status changes to `Working`, `Thinking`, tool-use output, or equivalent, and the input area is cleared.

If the message is only staged in the input area, it has not been handed off yet. Try `C-m` once; if still staged, stop and report the partial state rather than risking disruption.

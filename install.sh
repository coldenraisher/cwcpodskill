#!/usr/bin/env bash
# Install the four CWC podcast skills from this repo into ~/.claude/skills (macOS).
#   ./install.sh            link every skill that is not installed yet (symlink -> this repo; edits land in git)
#   ./install.sh --copy     copy instead of linking
#   ./install.sh --status   show what is installed where
# An existing ~/.claude/skills/<name> that is a real folder is NEVER replaced: it may hold built tools (tools/face,
# tools/expr) or local state. Move it aside yourself (to the Trash) if this repo should take over.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
DEST="${CLAUDE_SKILLS:-$HOME/.claude/skills}"
SKILLS=(CWC_PodCut CWC_PodClips CWC_PodReels CWC_PodRun)
MODE="${1:-link}"
mkdir -p "$DEST"
for s in "${SKILLS[@]}"; do
  src="$REPO/skills/$s"; dst="$DEST/$s"
  if [[ "$MODE" == "--status" ]]; then
    if [[ -L "$dst" ]]; then echo "$s -> $(readlink "$dst")"; elif [[ -d "$dst" ]]; then echo "$s: real folder (not from this repo)"; else echo "$s: not installed"; fi
    continue
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then echo "$s: already linked"; else echo "$s: $dst exists - left alone (move it aside to install from this repo)"; fi
    continue
  fi
  if [[ "$MODE" == "--copy" ]]; then cp -R "$src" "$dst"; echo "$s: copied"; else ln -s "$src" "$dst"; echo "$s: linked"; fi
done
[[ "$MODE" == "--status" ]] && exit 0
cat <<'EOF'

Next, once per machine:
  make -C ~/.claude/skills/CWC_PodCut/tools && make -C ~/.claude/skills/CWC_PodClips/tools && make -C ~/.claude/skills/CWC_PodReels/tools
  python3 ~/.claude/skills/CWC_PodReels/scripts/tg_router.py install    # PodReels' Telegram plugin
  python3 ~/.claude/skills/CWC_PodRun/scripts/tg_plan.py install        # PodRun's plan-card plugin
  python3 ~/.claude/skills/CWC_PodClips/scripts/tg_listen.py stop; python3 ~/.claude/skills/CWC_PodClips/scripts/tg_listen.py start
  python3 ~/.claude/skills/CWC_PodClips/scripts/doctor.py creative-lens
  python3 ~/.claude/skills/CWC_PodRun/scripts/selftest.py
EOF

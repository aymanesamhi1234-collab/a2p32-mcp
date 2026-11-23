#!/bin/bash
# publicar.sh -- crea/actualiza el repo en GitHub. Requiere gh autenticado.
set -euo pipefail
cd "$(dirname "$0")"

GH="${GH:-$HOME/.local/bin/gh}"
command -v "$GH" >/dev/null || { echo "falta gh"; exit 1; }
"$GH" auth status >/dev/null 2>&1 || {
  echo "gh sin autenticar. Ejecuta:  $GH auth login --web --git-protocol https"
  exit 1
}

OWNER=$("$GH" api user -q .login)
REPO=${REPO:-a2p32-mcp}
echo "cuenta: $OWNER · repo: $REPO"

for f in glama.json server.json README.md; do
  [ -f "$f" ] && sed -i '' "s/OWNER/$OWNER/g" "$f" 2>/dev/null || \
                 sed -i "s/OWNER/$OWNER/g" "$f"
done

if [ ! -d .git ]; then
  git init -q
  git checkout -q -b main
fi
git add -A
git -c user.name="$OWNER" -c user.email="$OWNER@users.noreply.github.com" \
    commit -qm "MCP client for A2P-32 Guard" || true

if ! "$GH" repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  "$GH" repo create "$OWNER/$REPO" --public --source=. --remote=origin --push \
        --description "MCP client for A2P-32 Guard: per-aspect limits and all-or-nothing batches for AI agents"
else
  git remote get-url origin >/dev/null 2>&1 || \
    git remote add origin "https://github.com/$OWNER/$REPO.git"
  git push -u origin main
fi

"$GH" repo edit "$OWNER/$REPO" --add-topic mcp --add-topic mcp-server \
      --add-topic x402 --add-topic ai-agents --add-topic guardrails \
      --add-topic usdc >/dev/null || true

echo "repo: https://github.com/$OWNER/$REPO"

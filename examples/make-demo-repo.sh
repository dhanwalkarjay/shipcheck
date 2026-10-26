#!/usr/bin/env bash
# Creates ./shipcheck-demo: a tiny git repo with a "main" branch and a risky
# "feature/checkout-retry" branch, so you can try ShipCheck without a real PR.
set -euo pipefail
rm -rf shipcheck-demo && mkdir shipcheck-demo && cd shipcheck-demo
git init -q -b main
git config user.email "demo@example.com"; git config user.name "demo"
mkdir -p src/auth migrations tests

cat > src/auth/session.py <<'PY'
import requests

def fetch_user(token):
    r = requests.get("https://id.example.com/me", headers={"Authorization": token})
    return r.json()
PY
cat > tests/test_checkout.py <<'PY'
def test_total():
    assert 1 + 1 == 2
    assert 2 + 2 == 4
PY
cat > tests/test_session.py <<'PY'
def test_fetch():
    assert True
PY
echo '{"name":"demo","dependencies":{"express":"4.18.2"}}' > package.json
cat > src/api.js <<'JS'
function handler(req, res) { res.send("ok"); }
module.exports = handler;
JS
cat > TASK.md <<'MD'
# Task: Add retry to checkout

Requirements:
1. Retry failed checkout requests up to 3 times.
2. Track the retry count per order in the database.
3. Add tests that cover the retry behaviour.
MD
git add -A && git commit -qm "base"

git checkout -qb feature/checkout-retry
cat > src/auth/session.py <<'PY'
import requests

API_KEY = "sk_live_abcdef1234567890"

def fetch_user(token):
    # TODO: remove verify=False once certs are fixed
    r = requests.get("https://id.example.com/me", headers={"Authorization": token}, verify=False)
    try:
        return r.json()
    except Exception:
        pass
PY
echo "ALTER TABLE orders ADD COLUMN retry_count INT NOT NULL DEFAULT 0;" > migrations/0042_add_retry.sql
echo '{"name":"demo","dependencies":{"express":"4.18.2","left-pad":"1.3.0","lodash":"4.17.21"}}' > package.json
cat > src/api.js <<'JS'
function handler(req, res) {
  console.log("debug", req.body);
  retry(req);
  res.send("ok");
}
module.exports = handler;
JS
git rm -q tests/test_checkout.py
cat > tests/test_session.py <<'PY'
import pytest

@pytest.mark.skip(reason="flaky")
def test_fetch():
    pass
PY
git add -A && git commit -qm "Add checkout retry"
git checkout -q main && git checkout -q feature/checkout-retry
echo "Demo repo ready: $(pwd)  (branch: feature/checkout-retry, base: main)"

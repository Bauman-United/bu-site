#!/usr/bin/env bash
# Проверка поднятого стека: ./deploy/smoke.sh [base_url]
set -euo pipefail
BASE="${1:-http://localhost}"
fail() { echo "FAIL: $*" >&2; exit 1; }
code() { curl -s -o /dev/null -w "%{http_code}" "$1"; }

for path in / /matches /standings /team /news /about /join /robots.txt /sitemap.xml; do
  c=$(code "$BASE$path"); [ "$c" = "200" ] || fail "$path → $c"
  echo "ok $path"
done
[ "$(code "$BASE/no-such-page")" = "404" ] || fail "404 page"
[ "$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/revalidate" -H 'content-type: application/json' -d '{"tags":["home"]}')" = "401" ] || fail "revalidate without secret must be 401"
curl -s "$BASE/" | grep -q 'application/ld+json' || fail "JSON-LD on home"
echo "smoke ok"

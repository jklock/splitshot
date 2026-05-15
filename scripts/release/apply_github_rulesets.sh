#!/usr/bin/env bash
set -euo pipefail

repo="jklock/splitshot"
api="repos/${repo}/rulesets"
owner_user_id="$(gh api user --jq '.id')"

branch_payload="$(mktemp)"
tag_payload="$(mktemp)"
trap 'rm -f "$branch_payload" "$tag_payload"' EXIT

cat >"$branch_payload" <<JSON
{
  "name": "Protect main",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    {
      "actor_id": ${owner_user_id},
      "actor_type": "User",
      "bypass_mode": "always"
    }
  ],
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/main"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "pull_request",
      "parameters": {
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["merge", "squash", "rebase"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "linux-tests" },
          { "context": "macos-tests" },
          { "context": "windows-tests" }
        ],
        "strict_required_status_checks_policy": true
      }
    }
  ]
}
JSON

cat >"$tag_payload" <<JSON
{
  "name": "Protect release tags",
  "target": "tag",
  "enforcement": "active",
  "bypass_actors": [
    {
      "actor_id": ${owner_user_id},
      "actor_type": "User",
      "bypass_mode": "always"
    }
  ],
  "conditions": {
    "ref_name": {
      "include": ["refs/tags/v*"],
      "exclude": []
    }
  },
  "rules": [
    {
      "type": "update",
      "parameters": {
        "update_allows_fetch_and_merge": false
      }
    },
    {
      "type": "deletion"
    }
  ]
}
JSON

upsert_ruleset() {
  local name="$1"
  local payload="$2"
  local existing_id
  existing_id="$(gh api "$api" --jq ".[] | select(.name == \"${name}\") | .id" 2>/dev/null || true)"
  if [[ -n "${existing_id}" ]]; then
    gh api "${api}/${existing_id}" --method PUT --input "$payload" >/dev/null
    echo "Updated ruleset: ${name} (${existing_id})"
  else
    gh api "$api" --method POST --input "$payload" >/dev/null
    echo "Created ruleset: ${name}"
  fi
}

upsert_ruleset "Protect main" "$branch_payload"
upsert_ruleset "Protect release tags" "$tag_payload"

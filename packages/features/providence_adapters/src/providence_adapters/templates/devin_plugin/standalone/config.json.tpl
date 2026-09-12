{
  "permissions": {
    "allow": [
      "Read(**)",
      "Exec(go test)",
      "Exec(go vet)",
      "Exec(go build)",
      "Exec(golangci-lint run)",
      "Exec(ruff check)",
      "Exec(ruff format --check)",
      "Exec(mypy)",
      "Exec(pytest)"
    ],
    "deny": [
      "Exec(git push)",
      "Exec(git reset)",
      "Exec(git rebase)",
      "Exec(git commit)",
      "Exec(git add)",
      "Exec(git merge)"
    ]
  },
  "mcpServers": {}
}

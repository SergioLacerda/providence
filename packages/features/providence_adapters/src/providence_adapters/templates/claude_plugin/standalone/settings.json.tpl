{
  "permissions": {
    "allow": [
      "Read(**)",
      "Bash(go test*)",
      "Bash(go vet*)",
      "Bash(go build*)",
      "Bash(golangci-lint run*)",
      "Bash(ruff check*)",
      "Bash(ruff format --check*)",
      "Bash(mypy*)",
      "Bash(pytest*)"
    ],
    "deny": [
      "Bash(git push*)",
      "Bash(git reset*)",
      "Bash(git rebase*)",
      "Bash(git commit*)",
      "Bash(git add*)",
      "Bash(git merge*)"
    ]
  }
}

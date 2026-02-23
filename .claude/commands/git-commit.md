---
allowed-tools: Bash(git status:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(git diff:*), Bash(git log:*), Bash(git ls-files:*), Bash(git grep:*), Grep, Glob, Read, AskUserQuestion
argument-hint: [commit-message]
description: Git commit and push to current branch
---

## Context

- Current git status: !`git status --short`
- Current branch: !`git branch --show-current`

## Your task

### 0. 보안 사전 검사 (커밋 전 필수)

**반드시 커밋 전에 아래 검사를 수행하라. 이 단계를 건너뛰면 안 된다.**

1. `git add .` 로 스테이징한 뒤, staged 파일 목록을 확인:
   ```
   git diff --cached --name-only
   ```

2. **민감 파일 패턴 검사** — staged 파일 중 아래 패턴에 해당하는 파일이 있는지 확인:
   - `.env`, `.env.*` (단 `.env.example`, `.env.sample` 제외)
   - `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`
   - `*.sk`, `*.skey`, `*.vkey`, `*.signing_key`
   - `key.json`, `credentials.json`, `service-account*.json`
   - `*.tfvars` (단 `*.tfvars.example` 제외), `*.tfstate`
   - `id_rsa`, `id_ed25519`, `id_ecdsa` (SSH 키)

3. **하드코딩된 시크릿 패턴 검사** — staged 파일의 diff 내용(`git diff --cached`)에서 아래 패턴 검색:
   - API 키: `(?i)(api[_-]?key|apikey)\s*[:=]\s*["'][A-Za-z0-9_\-]{20,}["']`
   - AWS 키: `AKIA[0-9A-Z]{16}`
   - Private 키 헤더: `-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----`
   - JWT/토큰: `(?i)(token|secret|password|passwd|jwt)\s*[:=]\s*["'][A-Za-z0-9_\-\.]{20,}["']`
   - Hex 개인키: `(?i)(private[_-]?key|signing[_-]?key)\s*[:=]\s*["']0x[0-9a-fA-F]{64}["']`
   - Mnemonic seed: `(?i)mnemonic\s*[:=]\s*["'](\w+\s+){11,}\w+["']`
   - GCP 서비스 계정: `"type"\s*:\s*"service_account"`

4. **결과 처리**:
   - 위험 항목이 **하나라도 발견되면**, 발견된 파일과 내용을 사용자에게 보고하고 `AskUserQuestion`으로 "이 파일/내용을 포함한 채 커밋을 진행할까요?" 확인을 받아라.
   - 사용자가 거부하면 해당 파일을 `git reset HEAD <file>`로 unstage하고 나머지만 커밋하라.
   - 위험 항목이 없으면 다음 단계로 진행하라.

**참고**: `.env.example`, `*.test.*`, `*_test.go`, `*.spec.*`, `docs/`, `CLAUDE.md`, `.claude/` 경로의 파일은 false positive가 많으므로 별도 표시하되 차단하지 않는다.

### 1. Commit & Push

1. The Current branch should not be main. (By default, stg is recommended.)
2. Analyze the staged changes and create an appropriate commit message
   - If `$ARGUMENTS` is provided, use it as the commit message
   - Otherwise, generate a commit message based on the changes
3. Commit and push to current branch

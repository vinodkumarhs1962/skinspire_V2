# Transcription (Speech To Text)

## One Time Setup

### 1. Change Directory
```shell
cd app/ml/transcription
```

### 2. Install UV (One-Time Installation)
```shell
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Linking Local <-> Modal
```shell
uv run modal setup
```

## Steps To Execute

### 1. UV Sync
```shell
uv sync --active
```

### 2. Deploy Service onto Modal
```shell
uv run --active modal deploy main.py
```
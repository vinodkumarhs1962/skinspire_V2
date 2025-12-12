# Transcription (Speech To Text)

## Architecture Diagram 
<img width="1300" height="456" alt="transcription-diagram" src="https://github.com/user-attachments/assets/4e7d06f6-3023-4a91-b12e-3b5b163bf47a" />


## Application Endpoint
Endpoint: https://intelli-clinic--transcription-api.modal.run

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

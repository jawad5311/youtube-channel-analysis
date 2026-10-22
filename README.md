# YouTube Channel Analysis

A modular YouTube channel analysis project with shared collectors, focused analysis skills, and quick-analysis workflows.

## Project areas

- `src/collectors/` collects channel metadata and recent video data.
- `src/analysis/` contains analysis logic for quick channel results.
- `src/workflows/` runs end-to-end analysis workflows.
- `skills/` contains the quick-analysis and specialist skill instructions.
- `tests/` contains offline tests using fake API clients.
- `runs/` stores local generated results and is ignored by Git.

## Setup

1. Create a virtual environment.
2. Install the dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Set `YOUTUBE_API_KEY` in `.env`.

The `.env` file and generated run data are excluded from Git.

## Run quick analysis

```powershell
python -m src.workflows.quick_channel_analysis https://youtube.com/@channelhandle
```

## Run tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The tests use fake clients and do not make YouTube API requests.

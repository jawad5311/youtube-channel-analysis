# Tests

The test suite uses Python's standard `unittest` runner and fake API clients, so it does not require network access or a YouTube API key.

Run all tests from the project root:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

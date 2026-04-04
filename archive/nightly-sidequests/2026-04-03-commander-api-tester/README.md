# API Tester

A simple, zero-dependency API testing tool created for Commander's sidequest.

## Features

- 🔍 HTTP/HTTPS requests (GET, POST, PUT, DELETE, etc.)
- 📊 Response validation and status code checking
- ⏱️ Response timing measurement
- 📝 Automatic report generation
- 🗂️ JSON response parsing
- 🚫 No external dependencies (uses Python standard library only)

## Usage

### Basic Usage

```bash
python3 api_tester.py sample_config.json
```

### Configuration Format

Create a JSON file with your API tests:

```json
{
  "tests": [
    {
      "name": "Test description",
      "url": "https://api.example.com/endpoint",
      "method": "GET",
      "headers": {
        "Authorization": "Bearer your-token",
        "Content-Type": "application/json"
      },
      "data": {
        "key": "value"
      },
      "timeout": 30
    }
  ]
}
```

### Configuration Options

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Test description |
| `url` | string | Yes | API endpoint URL |
| `method` | string | No | HTTP method (default: GET) |
| `headers` | object | No | Request headers |
| `data` | object/string | No | Request body (for POST/PUT) |
| `timeout` | number | No | Request timeout in seconds (default: 30) |

### Examples

#### GET Request
```json
{
  "name": "GitHub User",
  "url": "https://api.github.com/users/octocat",
  "method": "GET",
  "headers": {
    "Accept": "application/vnd.github.v3+json"
  }
}
```

#### POST Request
```json
{
  "name": "Create Post",
  "url": "https://jsonplaceholder.typicode.com/posts",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "data": {
    "title": "Hello World",
    "body": "Test content",
    "userId": 1
  }
}
```

## Output

The tool provides:
- Real-time test results with status indicators (✅/❌)
- Summary report with success rate
- Detailed results file (e.g., `sample_config_report.txt`)

## Files

- `api_tester.py` - Main testing script
- `sample_config.json` - Example configuration
- `README.md` - This file

## Testing

Run the example configuration:

```bash
python3 api_tester.py sample_config.json
```

## License

MIT - Created for Commander's sidequest
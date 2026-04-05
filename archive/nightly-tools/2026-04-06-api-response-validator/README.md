# API Response Validator

A self-contained, zero-dependency Python 3 CLI tool for validating HTTP JSON API responses against simple expectations.

## Features

- ✅ Validate required field existence
- ✅ Basic type checking (string, number, boolean, array, object, null)
- ✅ Enum value validation
- ✅ Multiple endpoints via single JSON config
- ✅ Fail-fast behavior (stops on first error)
- ✅ Human-readable error messages
- ✅ Zero external dependencies (Python stdlib only)

## Usage

```bash
python3 api-validator.py config.json
python3 api-validator.py config.json -e endpoint_name
```

## Config Format

```json
{
  "fail_fast": true,
  "endpoints": {
    "endpoint_name": {
      "url": "https://api.example.com/endpoint",
      "required": ["id", "name", "status"],
      "types": {
        "id": "number",
        "name": "string",
        "status": "string",
        "active": "boolean",
        "tags": "array"
      },
      "enums": {
        "status": ["active", "inactive"]
      }
    }
  }
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | The API endpoint URL to test |
| `required` | No | List of required field names |
| `types` | No | Map of field names to expected types |
| `enums` | No | Map of field names to allowed values |

### Supported Types

- `string` - Text values
- `number` - Integer or float
- `boolean` - true/false
- `array` - List/array
- `object` - Dictionary/object
- `null` - Null/None value

## Exit Codes

- `0` - All validations passed
- `1` - One or more validations failed

## Examples

### Basic Usage

```bash
# Validate all endpoints in config
python3 api-validator.py config.json

# Validate a specific endpoint
python3 api-validator.py config.json -e test_success
```

### Using File URLs for Testing

For local testing, you can use `file://` URLs pointing to sample JSON files:

```json
{
  "endpoints": {
    "local_test": {
      "url": "file:///path/to/sample.json",
      "required": ["id", "name"]
    }
  }
}
```

## Sample Files

- `config.json` - Example configuration with file-based test endpoints
- `sample-success.json` - Valid response example
- `sample-failure.json` - Invalid response example (type mismatch, missing fields)

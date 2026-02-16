# Release Notes Scraper

A robust tool for scraping and extracting release notes from Pure help center and similar sources.

## Features

### Core Functionality
- Scrape release notes from Pure help center pages
- Extract structured release note information
- Save release notes in clean markdown format
- Automatic content validation and quality checking

### Improved Features
- **Robust Error Handling**: Automatic retries with exponential backoff for failed requests
- **Comprehensive Logging**: Detailed logs to both console and file
- **Statistics Tracking**: Detailed scraping statistics with success rates
- **Command Line Interface**: Full configuration via command line arguments
- **Content Validation**: Automatic detection of invalid or error content
- **Retry Logic**: Configurable retry attempts for network issues
- **Polite Scraping**: Configurable delays between requests
- **Metadata Tracking**: Timestamps and source URLs preserved in output

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/release-notes-scraper.git
   cd release-notes-scraper
   ```

2. Install dependencies:
   ```bash
   pip install beautifulsoup4 html2text httpx readability-lxml
   ```

## Usage

### Basic Usage
```bash
python scraper.py --start 5290 --end 5300
```

### Advanced Options
```bash
# Scrape specific range with custom output
python scraper.py --start 5200 --end 5250 --output my_notes.md

# Adjust performance settings
python scraper.py --start 5000 --end 5100 --delay 1.0 --timeout 30.0 --retries 5

# Enable verbose logging for debugging
python scraper.py --start 5290 --end 5295 --verbose

# See all available options
python scraper.py --help
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--start` | 5290 | Starting page ID to scrape |
| `--end` | 5350 | Ending page ID to scrape |
| `--output` | pure_release_notes.md | Output file path |
| `--delay` | 0.5 | Delay between requests in seconds |
| `--timeout` | 15.0 | Request timeout in seconds |
| `--retries` | 3 | Maximum retries for failed requests |
| `--verbose` | False | Enable detailed logging |

## Output Files

The scraper generates several files:

1. **`pure_release_notes.md`** (or custom name):
   - Clean, formatted release notes in markdown
   - Includes metadata (source URLs, timestamps)
   - Structured with headers and separators

2. **`scraper_stats.json`**:
   - Detailed scraping statistics
   - Success rates, timing information
   - Error counts and performance metrics

3. **`scraper.log`**:
   - Complete logging of scraping process
   - Debug information for troubleshooting
   - Timestamps for all operations

## Output Format

The markdown output includes:
- Main header with generation timestamp
- Source URL for each release note
- Scraping timestamp
- Clean markdown content with proper formatting
- Section separators for readability

## Error Handling

The scraper handles various error conditions:
- **Network errors**: Automatic retries with exponential backoff
- **Timeouts**: Configurable timeout handling
- **Invalid content**: Content validation to filter out error pages
- **Rate limiting**: Detection and handling of 429 responses
- **SSL issues**: Configurable SSL verification

## Best Practices

1. **Start with small ranges**: Test with `--start X --end X+5` first
2. **Use delays**: Keep `--delay 0.5` or higher to be polite
3. **Monitor logs**: Check `scraper.log` for any issues
4. **Review statistics**: Check `scraper_stats.json` for success rates
5. **Incremental scraping**: Break large ranges into smaller batches

## Example Workflow

```bash
# Test a small range first
python scraper.py --start 5290 --end 5295

# Check the output
cat pure_release_notes.md

# Review statistics
cat scraper_stats.json

# If successful, scrape larger range
python scraper.py --start 5290 --end 5350 --delay 1.0
```

## Troubleshooting

### Common Issues

**SSL Certificate Errors**:
- If you encounter SSL errors, you may need to update your CA certificates
- For testing, you can modify the code to use `verify=False` (not recommended for production)

**No Pages Found**:
- Verify the page ID range is correct
- Check if the target website structure has changed
- Review the logs for detailed error information

**Slow Performance**:
- Reduce the `--delay` parameter (but be polite)
- Increase `--timeout` for slow networks
- Use `--retries 1` to minimize retry overhead

## License

[MIT License](LICENSE)
# Google Jobs Scraper

This Python script automates the process of scraping job postings from Google Jobs based on specified search terms. It leverages the Playwright library to interact with web pages, parse job details, and extract application links.

## TODO

- [x] Support a list of search terms
- [x] Run search terms after each other, just modifying the URL to bypass Captcha
- [x] Unify the output for it to be saved in a single JSON file when scraping multiple search terms
- [x] Improve CAPTCHA bypass by keeping browser window open throughout entire session
- [x] Implement JobSpy-style search term parsing with parentheses and OR logic
- [x] Enhanced search functionality using search box input instead of URL navigation
- [x] Append results to single file with duplicate prevention
- [ ] Add proxy rotation support for additional CAPTCHA evasion
- [ ] Implement retry mechanisms for failed searches
- [ ] Add support for location-based filtering within search terms

## Features

- Scrapes job postings from Google Jobs.
- **Advanced search term parsing** supports multiple formats:
  - Simple OR logic: `"software engineer" OR "data scientist"`
  - JobSpy-style with parentheses: `"engineering intern software (java OR python OR c++)"`
  - Complex combinations with multiple OR groups
- **CAPTCHA bypass** by keeping browser session open between searches.
- **Persistent browser session** - searches by typing in the search box rather than navigating to new URLs.
- Extracts detailed information about each job posting, including title, publisher, description, and application links.
- Filters jobs posted today (optional).
- Customizable search terms and job scraping limit per term.
- **Unified output** - all jobs from multiple search terms saved in a single JSON file with duplicate prevention.
- **Incremental scraping** - appends new results to existing files without duplicating jobs.

## Prerequisites

- Python 3.6+
- pip (Python package manager)

## Installation

### 1. Clone the Repository

Start by cloning the repository to your local machine:

```bash
git clone https://github.com/axsddlr/google_jobs_scraper.git
cd google_jobs_scraper
```

Replace `https://github.com/axsddlr/google_jobs_scraper.git` with the actual URL of your repository and `google_jobs_scraper` with the name of the folder where you cloned the repository.

### 2. Create a Virtual Environment (Optional but Recommended)

It's a good practice to create a virtual environment for Python projects to manage dependencies effectively. Use the following commands to create and activate a virtual environment:

- For macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

- For Windows:

```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

Install the required dependencies using pip:

```bash
pip install -r requirements.txt
```

This command will install all the necessary Python packages listed in `requirements.txt`, including Playwright.

### 4. Install Playwright Browsers

After installing the Playwright package, run the following command to install the required browsers:

```bash
playwright install
```

## Usage

To run the script, use the following command:

```bash
python google_jobs.py --search_terms="Your Search Terms" --limit=Number_of_Jobs_Per_Term --is_today --output_file="filename.json"
```

### Parameters

- `--search_terms`: Job search terms. Supports multiple formats:
  - Simple OR logic: `"software engineer" OR "data scientist" OR "machine learning engineer"`
  - JobSpy-style with parentheses: `"engineering intern software summer (java OR python OR c++) 2025"`
  - Complex combinations: `"data scientist (python OR r OR sql) remote"`
- `--limit`: Maximum number of jobs to scrape per search term (default: 50)
- `--is_today`: Optional flag to only scrape jobs posted today
- `--city_state`: Optional city and state filter (e.g., "New York,NY")
- `--output_file`: Output filename (default: "unified_jobs_scrape.json")

#### Performance/Timing Parameters (NEW)

- `--job_click_delay`: Delay in seconds between clicking job cards (default: 1.0)
- `--scroll_delay_min`: Minimum delay in seconds between scrolls (default: 2.0)
- `--scroll_delay_max`: Maximum delay in seconds between scrolls (default: 4.0)
- `--search_delay_min`: Minimum delay between different search terms (default: 3.0)
- `--search_delay_max`: Maximum delay between different search terms (default: 6.0)

### Examples

**Single search term:**

```bash
python google_jobs.py --search_terms="data scientist" --limit=100
```

**Multiple search terms with OR logic:**

```bash
python google_jobs.py --search_terms="software engineer" OR "data scientist" OR "machine learning engineer" --limit=75
```

**High-speed scraping with custom delays:**

```bash
python google_jobs.py --search_terms='"software engineer" OR "data scientist"' --limit=300 --job_click_delay=0.5 --scroll_delay_min=1.0 --scroll_delay_max=2.0 --search_delay_min=2.0 --search_delay_max=4.0
```

**Conservative scraping (slower but safer):**

```bash
python google_jobs.py --search_terms='"AI Engineer" OR "ML Engineer"' --limit=150 --job_click_delay=2.0 --scroll_delay_min=3.0 --scroll_delay_max=5.0
```

**JobSpy-style search with OR terms:**

```bash
python google_jobs.py --search_terms='"engineering intern" software summer (java OR python OR c++) 2025' --limit=100
```

**Complex JobSpy-style search:**

```bash
python google_jobs.py --search_terms="data scientist (python OR r OR sql) remote" --limit=75 --output_file="data_scientist_jobs.json"
```

**Multiple expanded searches from one JobSpy query:**

```bash
python google_jobs.py --search_terms="software engineer (python OR java OR javascript) (remote OR hybrid)" --limit=50
```

This will create searches for:

- "software engineer python remote"
- "software engineer python hybrid"
- "software engineer java remote"
- "software engineer java hybrid"
- "software engineer javascript remote"
- "software engineer javascript hybrid"

### How it Works

1. **CAPTCHA Bypass**: The script keeps the same browser window open throughout the entire scraping session
2. **Multiple Search Terms**: After scraping jobs for the first search term, it performs new searches by typing in the search box rather than opening new pages
3. **Unified Output**: All jobs from all search terms are saved in a single JSON file with metadata about which search term found each job
4. **Duplicate Prevention**: The script tracks scraped jobs across all search terms to avoid duplicates

## Output

The script saves the scraped job postings in a JSON file (default: `unified_jobs_scrape.json`) in the project directory. The output includes:

- **scrape_timestamp**: When the scraping was performed
- **total_jobs**: Total number of unique jobs scraped
- **jobs**: Array of job objects, each containing:
  - `scrape_time`: When this specific job was scraped
  - `search_term`: Which search term found this job
  - `job_title`: Job title
  - `publisher`: Company and location information
  - `time_posted`: When the job was posted (e.g., "2 days ago")
  - `salary`: Salary information if available
  - `benefits`: Array of benefits and requirements
  - `job_type`: Employment type (Full-time, Part-time, etc.)
  - `desc`: Job description
  - `application_links`: Array of application links with platform information

import json
import datetime
import logging
import time
import random
import argparse
import os
from playwright.sync_api import sync_playwright

GJOBS_URL = "https://www.google.com/search?q={}&ibp=htl;jobs"
GJOBS_URL_TODAY_SUBSTRING = (
    "#htivrt=jobs&htichips=date_posted:today&htischips=date_posted;today"
)
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"

OUTPUT_FILE_DIR = "unified_jobs_scrape.json"
THRESHOLD = 10
CAP = 50


class TimeKeeper:
    @property
    def now(self):
        """
        return the current correct date and time using the format specified
        """
        return f"{datetime.datetime.now():%d-%b-%Y T%I:%M}"


class css_selector:
    jobs_cards = "div.EimVGf"
    job_desc_card_visible = 'div[jsname="H9tDt"]'
    job_desc_tag = 'span[jsname="QAWWu"], span.us2QZb'
    title_tag = "h1.LZAQDf"
    publisher_tag = "div.waQ7qe"
    details_container = "div.mLdNec"
    detail_items = "div.nYym1e"
    detail_text = "span.RcZtZb"
    apply_link_cards = "span.fQYLde a"  # Updated to match the structure from examples


def scroll_element_into_view_and_click(element, page=None):
    """
    Scroll element into view and click with human-like behavior
    """
    try:
        # Ensure the element is visible in the viewport
        element.scroll_into_view_if_needed()

        # Add small random delay before clicking
        time.sleep(random.uniform(0.1, 0.3))

        # Get element position for more realistic clicking
        box = element.bounding_box()
        if box:
            # Click at a slightly random position within the element
            x_offset = random.uniform(0.2, 0.8) * box["width"]
            y_offset = random.uniform(0.3, 0.7) * box["height"]

            # Move mouse to element first (more human-like)
            element.hover()
            time.sleep(random.uniform(0.05, 0.15))

            # Click with slight offset from center
            element.click(position={"x": x_offset, "y": y_offset})
        else:
            # Fallback to regular click
            element.click()

    except Exception as e:
        logging.debug(f"Human-like click failed, using fallback: {e}")
        # Fallback to original click method
        element.scroll_into_view_if_needed()
        element.click()


def create_browser_context():
    playwright = sync_playwright().start()

    # Launch browser with stealth settings
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            # Basic stealth args
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-extensions-file-access-check",
            "--disable-extensions-http-throttling",
            "--disable-extensions-https-enforcement",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-client-side-phishing-detection",
            "--disable-component-extensions-with-background-pages",
            "--disable-default-apps",
            "--disable-hang-monitor",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-sync",
            "--disable-web-security",
            "--enable-automation=false",
            "--enable-blink-features=IdleDetection",
            "--no-default-browser-check",
            "--no-first-run",
            "--password-store=basic",
            "--use-mock-keychain",
            # Memory and performance
            "--memory-pressure-off",
            "--max_old_space_size=4096",
            # User agent and window size
            "--window-size=1920,1080",
        ],
    )

    # Create context with realistic settings
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        # Realistic browser settings
        locale="en-US",
        timezone_id="America/New_York",
        # Enable JavaScript
        java_script_enabled=True,
        # Accept downloads
        accept_downloads=True,
        # Realistic screen settings
        screen={"width": 1920, "height": 1080},
        # Device scale factor
        device_scale_factor=1,
        # Has touch (mobile simulation)
        has_touch=False,
        # Mobile simulation
        is_mobile=False,
        # Extra HTTP headers
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    # Add stealth scripts on every page
    context.add_init_script(
        """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock languages and plugins to look more realistic
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5], // Fake plugin array
        });
        
        // Override the `plugins` property to use a custom getter.
        Object.defineProperty(navigator, 'plugins', {
            get: function() {
                return [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ];
            }
        });
        
        // Overwrite the `chrome` object to avoid detection
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Hide automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    """
    )

    context.set_default_timeout(30000)  # Increased timeout for better stability
    return context


def add_random_mouse_movements(page):
    """
    Add random mouse movements to simulate human behavior
    """
    try:
        # Get viewport dimensions
        viewport = page.viewport_size
        width, height = viewport["width"], viewport["height"]

        # Perform 2-4 random mouse movements
        movements = random.randint(2, 4)
        for _ in range(movements):
            x = random.randint(100, width - 100)
            y = random.randint(100, height - 100)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        logging.debug(f"Random mouse movement failed: {e}")


def simulate_human_scroll(page, element_selector=None):
    """
    Simulate human-like scrolling behavior
    """
    try:
        if element_selector:
            element = page.query_selector(element_selector)
            if element:
                # Scroll to element first
                element.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.2, 0.5))

        # Random small scrolls to simulate reading
        scroll_steps = random.randint(2, 5)
        for _ in range(scroll_steps):
            # Small random scroll amounts
            scroll_delta = random.randint(100, 300)
            page.mouse.wheel(0, scroll_delta)
            time.sleep(random.uniform(0.3, 0.8))

            # Occasionally scroll back up a bit (like humans do)
            if random.random() < 0.3:
                page.mouse.wheel(0, -random.randint(50, 150))
                time.sleep(random.uniform(0.2, 0.4))

    except Exception as e:
        logging.debug(f"Human scroll simulation failed: {e}")


def simulate_human_typing(page, selector, text, clear_first=True):
    """
    Simulate human-like typing with realistic delays and occasional typos
    """
    try:
        element = page.query_selector(selector)
        if not element:
            return False

        element.click()
        time.sleep(random.uniform(0.2, 0.5))

        if clear_first:
            # Clear existing text
            element.fill("")
            time.sleep(random.uniform(0.1, 0.3))

        # Type character by character with human-like delays
        for i, char in enumerate(text):
            # Occasionally make a "typo" and correct it
            if random.random() < 0.02 and i > 2:  # 2% chance of typo
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                element.type(wrong_char)
                time.sleep(random.uniform(0.1, 0.3))
                # Backspace to correct
                element.press("Backspace")
                time.sleep(random.uniform(0.1, 0.3))

            # Type the correct character
            element.type(char)

            # Human-like typing speed variations
            if char == " ":
                time.sleep(random.uniform(0.1, 0.3))  # Longer pause after spaces
            elif char in ".,!?":
                time.sleep(random.uniform(0.2, 0.4))  # Pause after punctuation
            else:
                time.sleep(random.uniform(0.05, 0.15))  # Normal typing

        return True
    except Exception as e:
        logging.debug(f"Human typing simulation failed: {e}")
        return False


def random_delay(min_seconds=1.0, max_seconds=3.0):
    """
    Random delay with human-like patterns
    """
    delay = random.uniform(min_seconds, max_seconds)
    logging.debug(f"Random delay: {delay:.2f} seconds")
    time.sleep(delay)


def nap(secs=None):
    """
    sleeps the bot for specified number of seconds
    """
    if secs is None:
        secs = random.randint(0, 5)
    logging.info(f"Napping for {secs} seconds")
    print("nap for {} seconds".format(secs))
    time.sleep(secs)


def get_jobs(
    page,
    search_term,
    all_scraped_jobs,
    scraped_urls,
    cap,
    timing_config=None,
    output_file=None,
):
    if timing_config is None:
        timing_config = {
            "job_click_delay": 1.0,
            "scroll_delay_min": 2.0,
            "scroll_delay_max": 4.0,
        }

    timekeeper = TimeKeeper()
    current_search_jobs = []

    # Selector for the scrollable job list container
    job_list_container_selector = (
        "infinity-scrolling"  # This is the element that handles infinite scrolling
    )

    # Wait for the job list container to be visible
    page.wait_for_selector(job_list_container_selector)
    job_list_container = page.query_selector(job_list_container_selector)

    if not job_list_container:
        logging.error("Job list container not found.")
        return current_search_jobs

    previous_job_count = 0
    while True:
        # Scroll to the bottom of the job list container
        job_list_container.evaluate(
            "element => element.scrollTop = element.scrollHeight"
        )
        scroll_delay = random.uniform(
            timing_config["scroll_delay_min"], timing_config["scroll_delay_max"]
        )
        nap(scroll_delay)  # Give some time for new content to load

        job_cards = job_list_container.query_selector_all(css_selector.jobs_cards)
        current_job_count = len(job_cards)

        if current_job_count == previous_job_count and current_job_count > 0:
            logging.info("No new jobs loaded after scrolling. Breaking loop.")
            break

        # Process newly loaded job cards
        for i in range(previous_job_count, current_job_count):
            card = job_cards[i]
            try:
                # Click the job card to reveal its details
                scroll_element_into_view_and_click(card)
                # Give the page a moment to process the click with configurable delay
                nap(timing_config["job_click_delay"])
                # Wait for the job description card to be visible with increased timeout
                try:
                    page.wait_for_selector(
                        css_selector.job_desc_card_visible,
                        state="visible",
                        timeout=10000,
                    )
                except Exception as wait_error:
                    logging.warning(
                        f"Job description card not visible after clicking job {i}, trying alternative approach: {wait_error}"
                    )
                    # Try waiting a bit more and check again - use configurable delay
                    error_retry_delay = timing_config.get("error_retry_delay", 2.0)
                    nap(error_retry_delay)

                job_desc_card = page.query_selector(css_selector.job_desc_card_visible)
                if not job_desc_card:
                    logging.warning(
                        f"Job description card not found for job {i}, skipping"
                    )
                    continue

                job_data = scrape_job(timekeeper, job_desc_card, search_term)

                if job_data and job_data.get("application_links"):
                    # Use the first application link as a unique identifier
                    job_url = job_data["application_links"][0]["url"]
                    if job_url not in scraped_urls:
                        current_search_jobs.append(job_data)
                        all_scraped_jobs.append(job_data)
                        scraped_urls.add(job_url)
                        logging.info(
                            f"Successfully scraped job {len(current_search_jobs)} for '{search_term}': {job_data.get('job_title')}"
                        )

                        # Save the job immediately to the file
                        if output_file:
                            save_job_immediately(job_data, output_file)
                    else:
                        logging.info(
                            f"Skipping duplicate job: {job_data.get('job_title')}"
                        )
                elif job_data:
                    # If no application links, use a combination of title and publisher as a fallback unique identifier
                    unique_id = (
                        f"{job_data.get('job_title')}-{job_data.get('publisher')}"
                    )
                    if unique_id not in scraped_urls:
                        current_search_jobs.append(job_data)
                        all_scraped_jobs.append(job_data)
                        scraped_urls.add(unique_id)
                        logging.info(
                            f"Successfully scraped job {len(current_search_jobs)} for '{search_term}': {job_data.get('job_title')}"
                        )

                        # Save the job immediately to the file
                        if output_file:
                            save_job_immediately(job_data, output_file)

            except Exception as e:
                logging.error(f"Error processing job card {i}: {e}")
                # Continue to the next card even if one fails
                continue

            if len(current_search_jobs) >= cap:
                logging.info(
                    f"Reached CAP of {cap} jobs for search term '{search_term}'. Stopping."
                )
                break

        if len(current_search_jobs) >= cap:
            break

        previous_job_count = current_job_count
        short_delay = random.uniform(1, 3)  # Short nap before next scroll
        nap(short_delay)

    return current_search_jobs


def unpack_details(detail_elements):
    # Initialize default values
    time_posted = "Not specified"
    salary = "Not specified"
    job_type = "Not specified"
    benefits = []
    education = "Not specified"

    for detail in detail_elements:
        text_content = detail.text_content().strip()

        # Identify time posted (contains "ago" or "days")
        if any(
            keyword in text_content.lower()
            for keyword in ["ago", "day", "hour", "week", "month"]
        ):
            time_posted = text_content
        # Identify salary (contains currency symbols or "a year", "per hour", etc.)
        elif any(
            keyword in text_content
            for keyword in ["£", "$", "€", "a year", "per hour", "K–", "K "]
        ):
            salary = text_content
        # Identify job type (Full-time, Part-time, etc.)
        elif any(
            keyword in text_content
            for keyword in [
                "Full–time",
                "Full-time",
                "Part-time",
                "Contractor",
                "Contract",
                "Temporary",
                "Intern",
            ]
        ):
            job_type = text_content
        # Identify education requirements
        elif any(
            keyword in text_content
            for keyword in [
                "Degree",
                "Bachelor",
                "Master",
                "PhD",
                "Education",
                "No Degree",
            ]
        ):
            education = text_content
        # Everything else goes to benefits
        elif text_content and text_content not in ["Not specified"]:
            benefits.append(text_content)

    return time_posted, salary, job_type, benefits, education


def scrape_job(timekeeper, desc_card, search_term):
    scrape_time = timekeeper.now

    # Extract job title
    job_title_element = desc_card.query_selector(css_selector.title_tag)
    job_title = (
        job_title_element.text_content().strip()
        if job_title_element
        else "Title not found"
    )

    # Extract publisher info (company • location • via platform)
    publisher_element = desc_card.query_selector(css_selector.publisher_tag)
    publisher = (
        publisher_element.text_content().strip()
        if publisher_element
        else "Publisher not found"
    )

    # Extract job description
    job_desc_elements = desc_card.query_selector_all(css_selector.job_desc_tag)
    job_desc = ""
    for desc_element in job_desc_elements:
        job_desc += desc_element.text_content().strip() + " "
    job_desc = job_desc.strip() if job_desc else "Description not found"

    # Extract detail items (time posted, salary, job type, etc.)
    details_container = desc_card.query_selector(css_selector.details_container)
    detail_elements = []
    if details_container:
        detail_items = details_container.query_selector_all(css_selector.detail_items)
        for item in detail_items:
            text_element = item.query_selector(css_selector.detail_text)
            if text_element:
                detail_elements.append(text_element)

    # Extract application links
    application_links = []
    apply_link_elements = desc_card.query_selector_all(css_selector.apply_link_cards)
    for link_element in apply_link_elements:
        href = link_element.get_attribute("href")
        link_text = link_element.text_content().strip()

        # Extract platform name from the link text
        if "Apply on " in link_text:
            platform_name = link_text.replace("Apply on ", "").strip()
        else:
            platform_name = "Unknown Platform"

        if href:
            application_links.append({"url": href, "platform": platform_name})

    # Unpack details into specific variables
    time_posted, salary, job_type, benefits, education = unpack_details(detail_elements)

    # Add education to benefits if it's meaningful
    if education != "Not specified" and education not in benefits:
        benefits.append(f"Education: {education}")

    job_data = {
        "scrape_time": scrape_time,
        "search_term": search_term,
        "job_title": job_title,
        "publisher": publisher,
        "time_posted": time_posted,
        "salary": salary.replace("\u2013", "-"),
        "benefits": benefits,
        "job_type": job_type,
        "desc": job_desc,
        "application_links": application_links,
    }

    return job_data


def save_job_immediately(job_data, filename):
    """
    Save a single job immediately to the JSON file
    """
    try:
        # Load existing data
        existing_data = []
        existing_urls = set()

        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    file_data = json.load(f)
                    if isinstance(file_data, dict) and "jobs" in file_data:
                        existing_data = file_data["jobs"]
                    elif isinstance(file_data, list):
                        existing_data = file_data

                    # Track existing URLs to prevent duplicates - use same logic as main scraping
                    for job in existing_data:
                        if job.get("application_links"):
                            job_url = job["application_links"][0]["url"]
                            existing_urls.add(job_url)
                        else:
                            # Use fallback unique ID
                            unique_id = f"{job.get('job_title')}-{job.get('publisher')}"
                            existing_urls.add(unique_id)

            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = []
                existing_urls = set()

        # Check if this job already exists using same logic as main scraping
        job_identifier = None
        if job_data.get("application_links"):
            job_identifier = job_data["application_links"][0]["url"]
        else:
            job_identifier = f"{job_data.get('job_title')}-{job_data.get('publisher')}"

        if job_identifier in existing_urls:
            return False  # Job already exists, don't add it

        # Add the new job
        existing_data.append(job_data)

        # Create output data structure
        output_data = {
            "scrape_timestamp": datetime.datetime.now().isoformat(),
            "total_jobs": len(existing_data),
            "jobs": existing_data,
        }

        # Save to file
        with open(filename, "w") as f:
            json.dump(output_data, f, indent=4)

        logging.info(
            f"✅ Saved job immediately: {job_data.get('job_title')} (Total: {len(existing_data)} jobs)"
        )
        return True  # Job was added successfully

    except Exception as e:
        logging.error(f"Error saving job immediately to file: {e}")
        return False


def parse_search_terms(search_terms_input):
    """
    Parse search terms input to handle OR logic, including JobSpy-style syntax
    Examples:
    1. Simple OR: "software engineer" OR "data scientist" OR "machine learning"
    2. JobSpy style: "engineering intern software summer (java OR python OR c++)"
    3. Complex: "software engineer (python OR java OR c++) remote"
    """
    if not search_terms_input:
        return []

    # Check if this is a JobSpy-style search with parentheses
    if "(" in search_terms_input and ")" in search_terms_input:
        return expand_jobspy_search_terms(search_terms_input)

    # Handle simple OR separated terms
    terms = [
        term.strip().strip('"').strip("'") for term in search_terms_input.split(" OR ")
    ]
    return [term for term in terms if term]  # Remove empty terms


def expand_jobspy_search_terms(search_input):
    """
    Expand JobSpy-style search terms with parentheses containing OR logic
    Handles multiple OR groups properly
    Example: "software engineer (python OR java) (remote OR hybrid)"
    becomes: ["software engineer python remote", "software engineer python hybrid",
              "software engineer java remote", "software engineer java hybrid"]
    """
    import re

    # Find all parenthetical expressions with OR logic
    pattern = r"\(([^)]+)\)"
    matches = re.findall(pattern, search_input)

    if not matches:
        return [search_input]

    # Check if any of the matches actually contain OR
    has_or_logic = any(" OR " in match for match in matches)
    if not has_or_logic:
        # If no OR logic found in parentheses, treat as regular search term
        return [search_input]

    # Start with the base search term
    result_terms = [search_input]

    # Process each parenthetical group sequentially
    for match in matches:
        # Only process matches that contain OR logic
        if " OR " not in match:
            continue

        # Split the parenthetical content by OR
        or_terms = [term.strip().strip('"').strip("'") for term in match.split(" OR ")]
        or_terms = [term for term in or_terms if term]  # Remove empty terms

        # Expand each existing result term with each OR term
        new_result_terms = []
        for result_term in result_terms:
            for or_term in or_terms:
                # Replace the first occurrence of this parenthetical expression with the specific OR term
                pattern_to_replace = r"\(" + re.escape(match) + r"\)"
                expanded_term = re.sub(
                    pattern_to_replace, or_term, result_term, count=1
                )
                new_result_terms.append(expanded_term)

        result_terms = new_result_terms

    # Clean up extra spaces
    final_terms = []
    for term in result_terms:
        cleaned_term = " ".join(term.split())  # Remove extra whitespace
        if cleaned_term:
            final_terms.append(cleaned_term)

    return final_terms


def perform_new_search(page, search_term, is_today=False, timing_config=None):
    """
    Perform a new search by typing in the search box instead of navigating to a new URL
    This helps bypass CAPTCHA by keeping the same browser session
    """
    try:
        logging.info(f"Attempting to search for: '{search_term}'")

        # Multiple attempts to find and interact with search input
        search_selectors = [
            'input[type="text"]',
            'input[name="q"]',
            'input[title*="Search"]',
            'input[aria-label*="Search"]',
            '[role="searchbox"]',
        ]

        search_input = None
        selected_selector = None
        for selector in search_selectors:
            search_input = page.query_selector(selector)
            if search_input:
                selected_selector = selector
                logging.info(f"Found search input using selector: {selector}")
                break

        if search_input:
            # Add random mouse movements before interacting
            add_random_mouse_movements(page)

            # Ensure the search input is visible and focused
            search_input.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.2, 0.5))  # Human-like pause

            # Use human-like typing instead of direct input
            success = simulate_human_typing(
                page, selected_selector, search_term, clear_first=True
            )
            if not success:
                # Fallback to original method
                search_input.click()
                if timing_config:
                    nap(timing_config["job_click_delay"])
                else:
                    nap(1)

                # Clear existing content and type new search term
                page.keyboard.press("Control+a")
                page.keyboard.press("Delete")
                nap(0.5)
                page.keyboard.type(search_term, delay=50)

            # Random delay before submitting
            random_delay(0.5, 1.5)

            # Submit the search
            page.keyboard.press("Enter")

            # Wait for the page to load and jobs to appear
            page.wait_for_load_state("domcontentloaded")

            # Add some human-like scrolling after search
            simulate_human_scroll(page)

            # Wait for search results to load
            if timing_config:
                nap(
                    random.randint(
                        timing_config["search_delay_min"],
                        timing_config["search_delay_max"],
                    )
                )
            else:
                nap(random.randint(3, 5))  # fallback if no timing config
            # Try to wait for jobs to load with multiple attempts
            jobs_loaded = False
            for attempt in range(3):
                try:
                    page.wait_for_selector(css_selector.jobs_cards, timeout=10000)
                    jobs_loaded = True
                    break
                except Exception as wait_error:
                    logging.warning(
                        f"Attempt {attempt + 1}: Jobs not loaded yet, retrying... {wait_error}"
                    )
                    # Use configurable error retry delay
                    if timing_config:
                        nap(timing_config["error_retry_delay"])
                    else:
                        nap(2)  # fallback if no timing config

            if jobs_loaded:
                logging.info(f"Successfully performed new search for: '{search_term}'")
                return True
            else:
                logging.warning(f"Jobs did not load after search for: '{search_term}'")
                return False
        else:
            logging.warning(
                "Could not find any search input field, falling back to URL navigation"
            )
            return False

    except Exception as e:
        logging.error(f"Error performing new search for '{search_term}': {e}")
        return False


def save_results_to_file(all_jobs, filename):
    """
    Save all scraped jobs to a single JSON file, appending to existing data
    """
    try:
        # Check if file exists and load existing data
        existing_data = []
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    existing_file_data = json.load(f)
                    if (
                        isinstance(existing_file_data, dict)
                        and "jobs" in existing_file_data
                    ):
                        existing_data = existing_file_data["jobs"]
                    elif isinstance(existing_file_data, list):
                        existing_data = existing_file_data
            except (json.JSONDecodeError, KeyError):
                logging.warning(
                    f"Could not read existing file {filename}, starting fresh"
                )
                existing_data = []

        # Create a set of existing job identifiers to avoid duplicates when appending
        existing_identifiers = set()
        for job in existing_data:
            if job.get("application_links"):
                existing_identifiers.add(job["application_links"][0]["url"])
            else:
                # Fallback identifier
                identifier = f"{job.get('job_title')}-{job.get('publisher')}"
                existing_identifiers.add(identifier)

        # Filter out duplicates from new jobs
        new_jobs = []
        for job in all_jobs:
            if job.get("application_links"):
                identifier = job["application_links"][0]["url"]
            else:
                identifier = f"{job.get('job_title')}-{job.get('publisher')}"

            if identifier not in existing_identifiers:
                new_jobs.append(job)
                existing_identifiers.add(identifier)

        # Combine existing and new data
        combined_jobs = existing_data + new_jobs

        # Create output data structure
        output_data = {
            "scrape_timestamp": datetime.datetime.now().isoformat(),
            "total_jobs": len(combined_jobs),
            "new_jobs_added": len(new_jobs),
            "existing_jobs": len(existing_data),
            "jobs": combined_jobs,
        }

        # Save to file
        with open(filename, "w") as f:
            json.dump(output_data, f, indent=4)

        logging.info(
            f"Saved {len(combined_jobs)} total jobs to {filename} ({len(new_jobs)} new jobs added)"
        )

    except Exception as e:
        logging.error(f"Error saving results to file: {e}")


def scrape_multiple_search_terms(
    page, search_terms, is_today=False, cap=50, timing_config=None, output_file=None
):
    """
    Scrape jobs for multiple search terms in the same browser session
    """
    if timing_config is None:
        timing_config = {
            "job_click_delay": 1.0,
            "scroll_delay_min": 2.0,
            "scroll_delay_max": 4.0,
            "search_delay_min": 3.0,
            "search_delay_max": 6.0,
        }

    all_scraped_jobs = []
    scraped_urls = set()  # To track unique jobs across all searches

    for i, search_term in enumerate(search_terms):
        logging.info(f"Starting search {i+1}/{len(search_terms)}: '{search_term}'")
        # Perform new search (except for the first one which is already loaded)
        if i > 0:
            success = perform_new_search(page, search_term, is_today, timing_config)
            if not success:  # Fallback to URL navigation if search input method fails
                search_page_url = GJOBS_URL.format(search_term)
                if is_today:
                    search_page_url += GJOBS_URL_TODAY_SUBSTRING

                page.goto(search_page_url)
                handle_cookie_consent(page, timing_config)
        # Scrape jobs for current search term
        current_jobs = get_jobs(
            page,
            search_term,
            all_scraped_jobs,
            scraped_urls,
            cap,
            timing_config,
            output_file,
        )
        logging.info(
            f"Scraped {len(current_jobs)} jobs for search term: '{search_term}'"
        )

        # Small delay between searches to avoid being too aggressive
        if i < len(search_terms) - 1:  # Don't sleep after the last search
            delay = random.uniform(
                timing_config["search_delay_min"], timing_config["search_delay_max"]
            )
            nap(delay)

    return all_scraped_jobs


def handle_cookie_consent(page, timing_config=None):
    try:  # Try to find a button with "Accept all" text
        accept_button = page.query_selector('button:has-text("Accept all")')
        if not accept_button:
            # If not found, try a button with "I agree" text
            accept_button = page.query_selector('button:has-text("I agree")')
        if not accept_button:
            # If still not found, try a button with aria-label containing "Accept"
            accept_button = page.query_selector('button[aria-label*="Accept"]')

        if accept_button:
            accept_button.click()
            logging.info("Accepted cookie consent.")
            # Use configurable job click delay for cookies
            if timing_config:
                nap(timing_config["job_click_delay"])
            else:
                nap(1)  # fallback if no timing config
            # Wait for navigation or for the dialog to disappear
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)  # Give a moment for the page to settle
    except Exception as e:
        logging.info(f"No cookie consent dialog or failed to click accept: {e}")
        # Continue if no consent dialog appears or button not found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--search_terms",
        type=str,
        help="job terms to search for, separated by ' OR ' for multiple terms",
        required=True,
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="maximum number of jobs to scrape per search term (e.g., --limit=300 will scrape up to 300 jobs for each search term)",
        default=50,
    )
    parser.add_argument(
        "--is_today",
        action="store_true",
        help="Set this flag to only scrape jobs posted today",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        help="Output filename for the scraped jobs",
        default="unified_jobs_scrape.json",
    )
    parser.add_argument(
        "--job_click_delay",
        type=float,
        help="Delay in seconds between clicking job cards (default: 1.0)",
        default=1.0,
    )
    parser.add_argument(
        "--scroll_delay_min",
        type=float,
        help="Minimum delay in seconds between scrolls (default: 2.0)",
        default=2.0,
    )
    parser.add_argument(
        "--scroll_delay_max",
        type=float,
        help="Maximum delay in seconds between scrolls (default: 4.0)",
        default=4.0,
    )
    parser.add_argument(
        "--search_delay_min",
        type=float,
        help="Minimum delay in seconds between searches (default: 3.0)",
        default=3.0,
    )
    parser.add_argument(
        "--search_delay_max",
        type=float,
        help="Maximum delay in seconds between searches (default: 6.0)",
        default=6.0,
    )
    parser.add_argument(
        "--error_retry_delay",
        type=float,
        help="Delay in seconds when retrying after errors (default: 2.0)",
        default=2.0,
    )

    args = parser.parse_args()
    # Store timing configuration
    timing_config = {
        "job_click_delay": args.job_click_delay,
        "scroll_delay_min": args.scroll_delay_min,
        "scroll_delay_max": args.scroll_delay_max,
        "search_delay_min": args.search_delay_min,
        "search_delay_max": args.search_delay_max,
        "error_retry_delay": args.error_retry_delay,
    }

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Parse search terms
    search_terms = parse_search_terms(args.search_terms)
    if not search_terms:
        logging.error("No valid search terms provided")
        exit(1)

    logging.info(f"🤖 STEALTH MODE: Browser configured with anti-detection measures")
    logging.info(f"Will scrape for {len(search_terms)} search terms: {search_terms}")
    logging.info(f"Maximum jobs per search term: {args.limit}")
    logging.info(f"Timing config: {timing_config}")

    # Create browser context and page
    context = create_browser_context()
    page = context.new_page()

    try:
        # Start with the first search term
        first_search_term = search_terms[0]
        search_page_url = GJOBS_URL.format(first_search_term)
        if args.is_today:
            search_page_url += GJOBS_URL_TODAY_SUBSTRING

        logging.info(f"🔍 Navigating to Google Jobs with stealth techniques...")
        # Navigate to the first search
        page.goto(search_page_url)

        # Add human-like behavior after page load
        logging.info("🎭 Simulating human behavior...")
        add_random_mouse_movements(page)
        simulate_human_scroll(page)
        random_delay(1.0, 3.0)  # Random delay to look more human
        handle_cookie_consent(page, timing_config)
        # Scrape all search terms with correct limit and timing
        all_jobs = scrape_multiple_search_terms(
            page,
            search_terms,
            args.is_today,
            args.limit,
            timing_config,
            args.output_file,
        )

        # Note: Jobs are now saved immediately as they're scraped
        # The final save_results_to_file call ensures metadata is updated
        save_results_to_file(all_jobs, args.output_file)

        logging.info(f"Scraping completed! Total jobs scraped: {len(all_jobs)}")
        logging.info(f"Results saved to: {args.output_file}")

    finally:
        context.close()


if __name__ == "__main__":
    main()

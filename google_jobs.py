import json
import datetime
import logging
import time
import random
import argparse
from playwright.sync_api import sync_playwright

GJOBS_URL = "https://www.google.com/search?q={}&ibp=htl;jobs"
GJOBS_URL_TODAY_SUBSTRING = (
    "#htivrt=jobs&htichips=date_posted:today&htischips=date_posted;today"
)
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"

OUTPUT_FILE_DIR = "job_scrape_master.json"
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
    title_tag = 'h1.LZAQDf'
    publisher_tag = 'div.waQ7qe'
    details_container = 'div.mLdNec'
    detail_items = 'div.nYym1e'
    detail_text = 'span.RcZtZb'
    apply_link_cards = 'span.fQYLde a'  # Updated to match the structure from examples


def scroll_element_into_view_and_click(element):
    # Ensure the element is visible in the viewport
    element.scroll_into_view_if_needed()
    # Click the element
    element.click()


def create_browser_context():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent=user_agent, viewport={"width": 1920, "height": 1080}
    )
    context.set_default_timeout(20000)
    return context


def nap(secs=random.randint(0, 5)):
    """
    sleeps the bot for specified number of seconds
    """
    logging.info(f"Napping for {secs} seconds")
    print("nap for {} seconds".format(secs))
    time.sleep(secs)


def get_jobs(page):
    timekeeper = TimeKeeper()
    scraped_jobs = []
    scraped_urls = set()  # To keep track of unique job URLs
    
    # Selector for the scrollable job list container
    job_list_container_selector = 'infinity-scrolling' # This is the element that handles infinite scrolling

    # Wait for the job list container to be visible
    page.wait_for_selector(job_list_container_selector)
    job_list_container = page.query_selector(job_list_container_selector)

    if not job_list_container:
        logging.error("Job list container not found.")
        return

    previous_job_count = 0
    while True:
        # Scroll to the bottom of the job list container
        job_list_container.evaluate("element => element.scrollTop = element.scrollHeight")
        nap(random.randint(2, 4)) # Give some time for new content to load

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
                
                # Give the page a moment to process the click
                nap(1)
                
                # Wait for the job description card to be visible with increased timeout
                try:
                    page.wait_for_selector(css_selector.job_desc_card_visible, state='visible', timeout=10000)
                except Exception as wait_error:
                    logging.warning(f"Job description card not visible after clicking job {i}, trying alternative approach: {wait_error}")
                    # Try waiting a bit more and check again
                    nap(2)
                    
                job_desc_card = page.query_selector(css_selector.job_desc_card_visible)
                if not job_desc_card:
                    logging.warning(f"Job description card not found for job {i}, skipping")
                    continue
                    
                job_data = scrape_job(timekeeper, job_desc_card)
                
                if job_data and job_data.get("application_links"):
                    # Use the first application link as a unique identifier
                    job_url = job_data["application_links"][0]["url"]
                    if job_url not in scraped_urls:
                        scraped_jobs.append(job_data)
                        scraped_urls.add(job_url)
                        logging.info(f"Successfully scraped job {len(scraped_jobs)}: {job_data.get('job_title')}")
                    else:
                        logging.info(f"Skipping duplicate job: {job_data.get('job_title')}")
                elif job_data:
                    # If no application links, use a combination of title and publisher as a fallback unique identifier
                    unique_id = f"{job_data.get('job_title')}-{job_data.get('publisher')}"
                    if unique_id not in scraped_urls:
                        scraped_jobs.append(job_data)
                        scraped_urls.add(unique_id)
                        logging.info(f"Successfully scraped job {len(scraped_jobs)}: {job_data.get('job_title')}")

            except Exception as e:
                logging.error(f"Error processing job card {i}: {e}")
                # Continue to the next card even if one fails
                continue

            if len(scraped_jobs) >= CAP:
                logging.info(f"Reached CAP of {CAP} jobs. Stopping.")
                break

        if len(scraped_jobs) >= CAP:
            break

        previous_job_count = current_job_count
        nap(random.randint(1, 3)) # Short nap before next scroll

    output_data = {"search_page_url": search_page_url, "jobs": scraped_jobs}
    with open(OUTPUT_FILE_DIR, "w") as outfile:
        json.dump(output_data, outfile, indent=4)


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
        if any(keyword in text_content.lower() for keyword in ["ago", "day", "hour", "week", "month"]):
            time_posted = text_content
        # Identify salary (contains currency symbols or "a year", "per hour", etc.)
        elif any(keyword in text_content for keyword in ["£", "$", "€", "a year", "per hour", "K–", "K "]):
            salary = text_content
        # Identify job type (Full-time, Part-time, etc.)
        elif any(keyword in text_content for keyword in ["Full–time", "Full-time", "Part-time", "Contractor", "Contract", "Temporary", "Intern"]):
            job_type = text_content
        # Identify education requirements
        elif any(keyword in text_content for keyword in ["Degree", "Bachelor", "Master", "PhD", "Education", "No Degree"]):
            education = text_content
        # Everything else goes to benefits
        elif text_content and text_content not in ["Not specified"]:
            benefits.append(text_content)
    
    return time_posted, salary, job_type, benefits, education


def scrape_job(timekeeper, desc_card):
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


def format_city_state(city_state):
    if city_state:
        city, state = city_state.split(",")
        city = city.strip().replace(" ", "+")
        state = state.strip().replace(" ", "+")
        return f"&htichips=city;{city}_comma_%20{state}"
    return ""


parser = argparse.ArgumentParser()
parser.add_argument(
    "--search_term", type=str, help="job term to search for", required=True
)
parser.add_argument(
    "--limit", type=int, help="maximum number of jobs to scrape", default=50
)
parser.add_argument(
    "--is_today",
    action="store_true",
    help="Set this flag to only scrape jobs posted today",
)
parser.add_argument(
    "--city_state",
    type=str,
    help="City and state for job search, formatted as 'City,State' (e.g., 'New York,NY')",
)


args = parser.parse_args()
CAP = args.limit

context = create_browser_context()
page = context.new_page()
search_term = args.search_term
search_page_url = GJOBS_URL.format(search_term)
if args.is_today:
    search_page_url += GJOBS_URL_TODAY_SUBSTRING
if args.city_state:
    city_state_substring = format_city_state(args.city_state)
    search_page_url += city_state_substring
def handle_cookie_consent(page):
    try:
        # Try to find a button with "Accept all" text
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
            nap(random.randint(1, 2)) # Short nap after clicking
            # Wait for navigation or for the dialog to disappear
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_timeout(2000) # Give a moment for the page to settle
    except Exception as e:
        logging.info(f"No cookie consent dialog or failed to click accept: {e}")
        # Continue if no consent dialog appears or button not found

page.goto(search_page_url)
handle_cookie_consent(page) # Add this line
get_jobs(page)
context.close()

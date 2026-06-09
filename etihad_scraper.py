import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time

print("Starting Etihad Airways review scraper...")

base_url = "https://www.airlinequality.com/airline-reviews/etihad-airways"
pagesize = 100
# We will scrape 10 pages with 100 reviews per page, fetching up to 1,000 reviews.
total_pages = 10

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

data = []

# Column keys mapping
keys_map = {
    "Aircraft": "aircraft",
    "Type Of Traveller": "traveller_type",
    "Seat Type": "seat_type",
    "Route": "route",
    "Date Flown": "date_flown",
    "Seat Comfort": "seat_comfort",
    "Cabin Staff Service": "cabin_staff_service",
    "Food & Beverages": "food_beverages",
    "Inflight Entertainment": "entertainment",
    "Ground Service": "ground_service",
    "Wifi & Connectivity": "wifi",
    "Value For Money": "value_for_money",
    "Recommended": "recommended"
}

# The columns we want in our final CSV
columns_list = [
    "header", "author", "date", "place", "content", 
    "aircraft", "traveller_type", "seat_type", "route", "date_flown", 
    "recommended", "trip_verified", "rating",
    "seat_comfort", "cabin_staff_service", "food_beverages", 
    "ground_service", "value_for_money", "entertainment", "wifi"
]

for page in range(1, total_pages + 1):
    url = f"{base_url}/page/{page}/?sortby=post_date%3ADesc&pagesize={pagesize}"
    print(f"Scraping page {page} of {total_pages}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code} for page {page}. Skipping.")
            continue
            
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("article", itemprop="review")
        
        if not articles:
            print(f"No reviews found on page {page}. Ending scraping early.")
            break
            
        for art in articles:
            row_data = {col: None for col in columns_list}
            
            # Header
            header_el = art.find("h2", class_="text_header")
            row_data["header"] = header_el.text.strip().strip('"').strip('“').strip('”') if header_el else None
            
            # Rating
            rating_el = art.find("span", itemprop="ratingValue")
            row_data["rating"] = int(rating_el.text.strip()) if rating_el and rating_el.text.strip().isdigit() else None
            
            # Author & Place/Country
            author_el = art.find("span", itemprop="author")
            author = None
            place = None
            if author_el:
                author_span = author_el.find("span", itemprop="name")
                author = author_span.text.strip() if author_span else author_el.text.strip()
                
                parent_text = author_el.parent.text if author_el.parent else ""
                match = re.search(r'\((.*?)\)', parent_text)
                if match:
                    place = match.group(1).strip()
            row_data["author"] = author
            row_data["place"] = place

            # Date Published
            date_el = art.find("time", itemprop="datePublished")
            row_data["date"] = date_el["datetime"] if date_el and date_el.has_attr("datetime") else (date_el.text.strip() if date_el else None)
            
            # Text Content & Verification
            content_el = art.find("div", class_="text_content")
            content = content_el.text.strip() if content_el else ""
            trip_verified = "Not Verified"
            if "Trip Verified" in content:
                trip_verified = "Verified"
                content = re.sub(r'^.*?Trip Verified\s*\|\s*', '', content, flags=re.IGNORECASE)
            elif "Not Verified" in content:
                trip_verified = "Not Verified"
                content = re.sub(r'^.*?Not Verified\s*\|\s*', '', content, flags=re.IGNORECASE)
            row_data["trip_verified"] = trip_verified
            row_data["content"] = content.strip()
            
            # Review ratings table
            ratings_table = art.find("table", class_="review-ratings")
            if ratings_table:
                for row in ratings_table.find_all("tr"):
                    header_td = row.find("td", class_="review-rating-header")
                    value_td = row.find("td", class_="review-value")
                    stars_td = row.find("td", class_="review-rating-stars")
                    
                    if header_td:
                        key = header_td.text.strip()
                        csv_key = keys_map.get(key)
                        if csv_key:
                            val = None
                            if value_td:
                                val = value_td.text.strip()
                            elif stars_td:
                                val = len(stars_td.find_all("span", class_="star fill"))
                            row_data[csv_key] = val
                            
            data.append(row_data)
            
        # Add a polite delay between page requests
        time.sleep(1)
        
    except Exception as e:
        print(f"Exception occurred on page {page}: {e}")
        continue

# Create DataFrame and save to CSV
if data:
    df = pd.DataFrame(data)
    # Reorder columns to match standard structure
    df = df[columns_list]
    
    # Save CSV
    output_filename = "etihad_reviews.csv"
    df.to_csv(output_filename, index=False)
    print(f"\nScraping finished successfully!")
    print(f"Total reviews scraped: {len(df)}")
    print(f"Dataset saved to: {output_filename}")
else:
    print("\nError: No review data scraped.")

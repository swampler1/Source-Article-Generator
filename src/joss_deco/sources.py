from __future__ import annotations

import os
import pandas as pd
from bs4 import BeautifulSoup
import requests
from astroquery.simbad import Simbad
from .utils import safe_slug


# Scrapes an HTML table from a URL and returns it as a pandas DataFrame
def _parse_html_table(table) -> pd.DataFrame:
    headers = [header.text.strip() for header in table.find_all("th")]
    rows = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        row_data = [cell.text.strip() for cell in cells]
        rows.append(row_data)
    return pd.DataFrame(rows, columns=headers if headers else None)


def scrape_table(url, table_index=0):
    """
    Finds tables from webpage using given url and scrapes their contents into a DataFrame
    ---
    Parameters
    url: (str) Link to webpage of interest containing at least one table
    (opt) table_index: (int) Selects which table to parse if page contains more than one, defaults to 0 (first one)
    ---
    Returns
    df: (Data Frame) Webpage table contents
    """

    # Send a GET request to the webpage
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for failed requests

    # Parse the webpage content
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all tables on the webpage
    tables = soup.find_all("table")

    if not tables:
        print("No tables found on the webpage.")
        return None

    # Select the desired table (default is the first one)
    table = tables[table_index]

    return _parse_html_table(table)


def get_simbad_aliases(name: str):
    """Return (canonical_main_id, aliases_list) for a SIMBAD object."""
    try:
        s = Simbad()
        s.add_votable_fields("ids")
        t = s.query_object(name)
        if t is None or len(t) == 0:
            return name, []
        canonical = str(t["MAIN_ID"][0])

        ids_tbl = Simbad.query_objectids(name)
        aliases = [str(row["ID"]) for row in ids_tbl] if ids_tbl is not None else []
        return canonical, aliases
    except Exception:
        return name, []


def get_disk_lit(disk_name_orig, save_dir="Scraped_Table_Data"):
    """
    Retrieves scored literature information from SIMBAD for a given disk and saves it as a .csv to desired folder
    ---
    Parameters
    disk_name_orig: (str) Plain text name of disk of interest. Any name recognized by SIMBAD should work
                    (i.e. "2MASS J16004452-4155310" should return the same result as "MY Lup")
    (opt) save_dir: (str) Name of folder to which the .csv will be saved, defaults to "Scraped_Table_Data"
    """

    # Create versions of disk name for web-searchability and file saving
    disk_name = disk_name_orig.replace(" ", "%20")
    disk_name_file = safe_slug(disk_name_orig)

    # Dynamically construct the SIMBAD URL without a hardcoded identifier
    baseurl = "https://simbad.cds.unistra.fr/simbad/sim-id-refs?Ident="
    url = baseurl + disk_name

    # Scrape SIMBAD and detect the literature table by headers
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")

    df = None
    required_cols = {"Score", "Bibcode/DOI"}
    for table in tables:
        try:
            candidate = _parse_html_table(table)
        except Exception:
            continue
        if candidate is not None and required_cols.issubset(set(candidate.columns)):
            df = candidate
            break

    # Fallback to legacy index for compatibility
    if df is None:
        try:
            df = scrape_table(url, table_index=2)
        except Exception:
            df = None

    if df is not None:
        filtered_df = df[df["Score"] != ""]
        filtered_df.loc[:, "Score"] = filtered_df["Score"].astype(int)  # so not treated as strings
        df_sorted = filtered_df.sort_values(by="Score", ascending=False)
        # print(df_sorted)
        print(f"\nTop SIMBAD literature for {disk_name_orig} (sorted by score):")
        print(df_sorted.head(10))  # show top 10 rows nicely
        os.makedirs(save_dir, exist_ok=True)
        df_sorted.to_csv(save_dir + "/%s_scraped_table.csv" % (disk_name_file), index=False)  # Save to CSV


# Selects top papers for a disk from the scraped SIMBAD table based on score and limit
def select_papers(disk_name_orig, score_limit=0, paper_limit=5, scraped_table_dir="Scraped_Table_Data"):
    # Create version of disk name for file reading
    disk_name_file = safe_slug(disk_name_orig)

    papers = []

    # Read CSV
    df_Literature = pd.read_csv(os.path.join(scraped_table_dir, disk_name_file + r"_scraped_table.csv"), index_col=False)

    count = 0
    for i in range(len(df_Literature)):
        if count >= paper_limit:
            break
        if df_Literature["Score"][i] > score_limit:
            bibcode = df_Literature["Bibcode/DOI"][i]
            authors = df_Literature["First \n3\n Authors"][i]  # Use exact column name
            papers.append({"bibcode": bibcode, "authors": authors})
            count += 1

    num_papers = len(papers)
    if num_papers == 0:
        print(f"No literature exists for {disk_name_orig} within given parameters. Consider adjusting your score limit.")
    elif num_papers == 1:
        print(f"Only 1 paper found for {disk_name_orig} with SIMBAD score over {score_limit}")
    elif num_papers < paper_limit:
        print(f"Only {num_papers} papers found for {disk_name_orig} with SIMBAD scores over {score_limit}")
    else:
        print(f"{num_papers} papers found for {disk_name_orig}")

    return papers

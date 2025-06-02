def get_chrome_driver():
    """Configure Chrome driver for cloud deployment"""
    chrome_options = Options()
    
    # Essential options for cloud deployment
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
    
    # Try to use system chromium first, then fall back to webdriver-manager
    try:
        # For Streamlit Cloud and similar platforms
        chrome_options.binary_location = "/usr/bin/chromium"
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except:
        try:
            # Fallback using webdriver-manager
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except:
            # Last resort - try default
            driver = webdriver.Chrome(options=chrome_options)
            return driver
# Configure the page
st.set_page_config(
    page_title="Recent Data Breaches",
    page_icon="🔒",
    layout="wide"
)

# Title
st.title("Recently Reported Data Breaches")

# Maine breach function
def maine_breach_table():
    driver = get_chrome_driver()
    driver.get('https://www.maine.gov/agviewer/content/ag/985235c7-cb95-4be2-8792-a1252b4f8318/list.html')
    urls = []
    df_list = []
    
    # Gather URLs of individual breach report pages
    for i in driver.find_elements(By.TAG_NAME, 'a'): 
        if len(str(i.get_attribute("href"))) > 100:
            urls.append(i.get_attribute("href"))
    
    # Visit each URL and gather breach report data
    for x in urls:
        driver.get(x)
        q = [i for i in driver.find_element(By.XPATH, '//*[@id="content"]').text.split("\n") if ": " in i]
        data_dict = {'URL': x}  # Initialize dictionary with URL
        for item in q:
            key, value = item.split(': ', 1)  # Split on first occurrence of ': '
            data_dict[key] = value
        df_list.append(data_dict)  # Append dictionary to list
    
    # Convert list of dictionaries to DataFrame
    df = pd.DataFrame(df_list)
    
    # Ensure specific columns are present and add missing ones if necessary
    columns = [
        'Entity Name', 'Total number of persons affected (including residents)', 'Street Address', 'City',
        'State, or Country if outside the US', 'Zip Code', 'Name', 'Date(s) Breach Occured',
        'Date Breach Discovered', 'Type of Notification', 'Date(s) of consumer notification',
        'Copy of notice to affected Maine residents', 'URL'
    ]
    for col in columns:
        if col not in df.columns:
            df[col] = None  # Fill missing columns with None values

    # Convert specific columns to numeric and datetime formats
    df['Total number of persons affected (including residents)'] = pd.to_numeric(
        df['Total number of persons affected (including residents)'], errors="coerce")
    df['Date(s) of consumer notification'] = pd.to_datetime(df['Date(s) of consumer notification'], errors='coerce')
    
    # Sort by notification date and remove duplicates
    df = df.sort_values(by="Date(s) of consumer notification", ascending=False).drop_duplicates()
    
    driver.quit()
    return df

# Texas breach function
def breach_report_tx():
    driver = get_chrome_driver()
    driver.get('https://oag.my.site.com/datasecuritybreachreport/apex/DataSecurityReportsPage')
    
    try:
        # Wait up to 10 seconds for the element to be present and clickable
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="mycdrs_last"]'))
        )
        element.click()
        
        # Extract the main breach table
        df_tx = pd.read_html(driver.page_source)[0]
        
        # Rename columns to match Maine's column names
        df_tx.columns = [
            'Entity Name', 'Entity or Individual Address', 'City', 'State',
            'Zip Code', 'Type of Notification', 'Total number of persons affected (including residents)',
            'Notice Provided to Consumers (Y/N)', 'Method(s) of Notice to Consumers', 'Date Published at OAG Website'
        ]
        
        # Add URL column with the Texas main URL
        df_tx['URL'] = 'https://oag.my.site.com/datasecuritybreachreport/apex/DataSecurityReportsPage'
    except TimeoutException:
        print("Timed out waiting for element to be clickable")
        driver.quit()
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        driver.quit()
        return None
    finally:
        driver.quit()
        
    return df_tx

# Hawaii Table
def hawaii_db():
    driver = get_chrome_driver()
    driver.get(
    "https://cca.hawaii.gov/ocp/notices/security-breach/#:~:text=Any%20business%20or%20government%20agency,2%28f%29%2C%20Hawaii%20Revised%20Statutes")
    df = pd.read_html(driver.page_source)[0]
    driver.quit()
    return df

def washington_db():
    driver = get_chrome_driver()
    driver.get("https://www.atg.wa.gov/data-breach-notifications")
    df = pd.read_html(driver.page_source)[0]
    driver.quit()
    return df

# Cleaning functions
def clean_maine_data(df):
    """Clean and standardize Maine data"""
    if df is None or df.empty:
        return None
    
    df_clean = df.copy()
    
    # Extract the needed columns
    columns_to_extract = []
    if 'Entity Name' in df.columns:
        columns_to_extract.append('Entity Name')
    if 'Total number of persons affected (including residents)' in df.columns:
        columns_to_extract.append('Total number of persons affected (including residents)')
    if 'Total number of Maine residents affected' in df.columns:
        columns_to_extract.append('Total number of Maine residents affected')
    if 'Date(s) of consumer notification' in df.columns:
        columns_to_extract.append('Date(s) of consumer notification')
    if 'URL' in df.columns:
        columns_to_extract.append('URL')
    
    df_clean = df_clean[columns_to_extract]
    
    # Rename columns
    df_clean = df_clean.rename(columns={
        'Entity Name': 'entity_name',
        'Total number of persons affected (including residents)': 'total_affected',
        'Total number of Maine residents affected': 'state_residents_affected',
        'Date(s) of consumer notification': 'date_reported',
        "URL": 'source_link'
    })
    
    df_clean['reporting_state_agency'] = 'ME'
    
    # Convert dates
    if 'date_reported' in df_clean.columns:
        df_clean['date_reported'] = pd.to_datetime(df_clean['date_reported'], errors='coerce')
    
    # Convert numeric
    for num_col in ['total_affected', 'state_residents_affected']:
        if num_col in df_clean.columns:
            df_clean[num_col] = pd.to_numeric(df_clean[num_col], errors='coerce')
    
    return df_clean

def clean_hhs_data(df):
    """Clean and standardize HHS data"""
    if df is None or df.empty:
        return None
    
    df_clean = df.copy()
    
    # Extract needed columns
    columns_to_extract = []
    if 'Name of Covered Entity' in df.columns:
        columns_to_extract.append('Name of Covered Entity')
    if 'Individuals Affected' in df.columns:
        columns_to_extract.append('Individuals Affected')
    if 'Breach Submission Date' in df.columns:
        columns_to_extract.append('Breach Submission Date')
    
    df_clean = df_clean[columns_to_extract]
    
    # Rename columns
    df_clean = df_clean.rename(columns={
        'Name of Covered Entity': 'entity_name',
        'Individuals Affected': 'total_affected',
        'Breach Submission Date': 'date_reported'
    })
    
    df_clean['source_link'] = 'https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf'
    df_clean['reporting_state_agency'] = 'HHS'
    
    # For HHS, we don't have state-specific data
    df_clean['state_residents_affected'] = np.nan
    
    # Convert dates
    df_clean['date_reported'] = pd.to_datetime(df_clean['date_reported'], errors='coerce')
    
    # Convert numeric
    df_clean['total_affected'] = pd.to_numeric(df_clean['total_affected'], errors='coerce')
    
    return df_clean

def clean_texas_data(df):
    """Clean and standardize Texas data"""
    if df is None or df.empty:
        return None
    
    df_clean = df.copy()
    
    # Extract needed columns
    columns_to_extract = []
    if 'Entity Name' in df.columns:
        columns_to_extract.append('Entity Name')
    if 'Total number of persons affected (including residents)' in df.columns:
        columns_to_extract.append('Total number of persons affected (including residents)')
    if 'Date Published at OAG Website' in df.columns:
        columns_to_extract.append('Date Published at OAG Website')
    if 'URL' in df.columns:
        columns_to_extract.append('URL')
    
    df_clean = df_clean[columns_to_extract]
    
    # Rename columns
    df_clean = df_clean.rename(columns={
        'Entity Name': 'entity_name',
        'Total number of persons affected (including residents)': 'state_residents_affected',  # TX reports state numbers
        'Date Published at OAG Website': 'date_reported',
        'URL': 'source_link'
    })
    
    df_clean['reporting_state_agency'] = 'TX'
    
    # For Texas, we don't have national total
    df_clean['total_affected'] = np.nan
    
    # Convert dates
    df_clean['date_reported'] = pd.to_datetime(df_clean['date_reported'], errors='coerce')
    
    # Convert numeric
    df_clean['state_residents_affected'] = pd.to_numeric(df_clean['state_residents_affected'], errors='coerce')
    
    return df_clean

def clean_washington_data(df):
    """Clean and standardize Washington data"""
    if df is None or df.empty:
        return None
    
    df_clean = df.copy()
    
    # Create new dataframe with extracted data
    data = []
    for _, row in df_clean.iterrows():
        entry = {}
        
        # Extract entity name
        if 'Organization Name' in row:
            org_name = str(row['Organization Name'])
            entity_name = org_name.replace('Organization Name ', '')
            entry['entity_name'] = entity_name
        
        # Extract date reported
        if 'Date Reported' in row:
            date_reported = str(row['Date Reported'])
            date_reported = date_reported.replace('Date Reported ', '')
            entry['date_reported'] = pd.to_datetime(date_reported, errors='coerce')
        
        # Extract number of WA residents affected
        if 'Number of Washingtonians Affected' in row:
            wa_affected = str(row['Number of Washingtonians Affected'])
            wa_affected = wa_affected.replace('Number of Washingtonians Affected ', '')
            entry['state_residents_affected'] = pd.to_numeric(wa_affected, errors='coerce')
        
        entry['source_link'] = 'https://www.atg.wa.gov/data-breach-notifications'
        entry['reporting_state_agency'] = 'WA'
        
        # We don't have total affected for WA
        entry['total_affected'] = np.nan
        
        data.append(entry)
    
    df_clean = pd.DataFrame(data)
    
    return df_clean

def clean_hawaii_data(df):
    """Clean and standardize Hawaii data"""
    if df is None or df.empty:
        return None
    
    df_clean = df.copy()
    
    # Extract needed columns
    columns_to_extract = []
    if 'Breached Entity Name' in df.columns:
        columns_to_extract.append('Breached Entity Name')
    if 'Date Notified' in df.columns:
        columns_to_extract.append('Date Notified')
    if 'Hawaii Residents Impacted' in df.columns:
        columns_to_extract.append('Hawaii Residents Impacted')
    if 'Link to Letter' in df.columns:
        columns_to_extract.append('Link to Letter')
    
    df_clean = df_clean[columns_to_extract]
    
    # Rename columns
    df_clean = df_clean.rename(columns={
        'Breached Entity Name': 'entity_name',
        'Date Notified': 'date_reported',
        'Hawaii Residents Impacted': 'state_residents_affected',
        'Link to Letter': 'source_link'
    })
    
    if 'source_link' in df_clean.columns:
        df_clean['source_link'] = df_clean['source_link'].fillna('https://cca.hawaii.gov/ocp/notices/security-breach/')
    
    df_clean['reporting_state_agency'] = 'HI'
    
    # We don't have total affected for HI
    df_clean['total_affected'] = np.nan
    
    # Convert dates
    if 'date_reported' in df_clean.columns:
        df_clean['date_reported'] = df_clean['date_reported'].apply(
            lambda x: pd.to_datetime(str(x).replace('.', '/'), errors='coerce', format='%Y/%m/%d')
            if isinstance(x, str) else pd.NaT
        )
    
    # Convert numeric
    df_clean['state_residents_affected'] = pd.to_numeric(df_clean['state_residents_affected'], errors='coerce')
    
    return df_clean

def clean_california_data(df):
    """Clean and standardize California data"""
    if df is None or df.empty:
        return None
    
    df_clean = df.copy()
    
    # Rename columns
    df_clean = df_clean.rename(columns={
        'Organization Name': 'entity_name',
        'Reported Date': 'date_reported'
    })
    
    df_clean['reporting_state_agency'] = 'CA'
    df_clean['source_link'] = 'https://oag.ca.gov/privacy/databreach/list'
    
    # California doesn't provide affected numbers
    df_clean['total_affected'] = np.nan
    df_clean['state_residents_affected'] = np.nan
    
    # Convert dates
    if 'date_reported' in df_clean.columns:
        df_clean['date_reported'] = pd.to_datetime(df_clean['date_reported'], errors='coerce')
    
    return df_clean

def final_cleaning(df):
    """Perform final cleaning and standardization"""
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_clean = df.copy()
    
    # Ensure all required columns exist
    required_columns = [
        'entity_name', 
        'total_affected', 
        'state_residents_affected',
        'date_reported', 
        'reporting_state', 
        'source_link'
    ]
    
    for col in required_columns:
        if col not in df_clean.columns:
            df_clean[col] = np.nan
    
    # Handle duplicates
    if not df_clean.empty:
        df_clean['nan_count'] = df_clean.isna().sum(axis=1)
        df_clean = df_clean.sort_values(['entity_name', 'date_reported', 'nan_count'])
        df_clean = df_clean.drop_duplicates(subset=['entity_name', 'date_reported'], keep='first')
        df_clean = df_clean.drop('nan_count', axis=1)
    
    # Standardize dates
    for date_col in ['date_reported', 'date_breach_occurred', 'date_breach_discovered']:
        if date_col in df_clean.columns:
            df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors='coerce')
    
    # Standardize numeric columns
    for num_col in ['total_affected', 'state_residents_affected']:
        if num_col in df_clean.columns:
            if df_clean[num_col].dtype == 'object':
                df_clean[num_col] = df_clean[num_col].apply(
                    lambda x: pd.to_numeric(re.sub(r'[^\d.]', '', str(x)) if str(x).strip() else np.nan, 
                                           errors='coerce')
                )
    
    # Fill missing date_breach_occurred
    if 'date_breach_occurred' in df_clean.columns and 'date_breach_discovered' in df_clean.columns:
        mask = df_clean['date_breach_occurred'].isna() & df_clean['date_breach_discovered'].notna()
        df_clean.loc[mask, 'date_breach_occurred'] = df_clean.loc[mask, 'date_breach_discovered']
    
    # Sort by date reported
    df_clean = df_clean.sort_values('date_reported', ascending=False)
    df_clean = df_clean.reset_index(drop=True)
    
    return df_clean

@st.cache_data(ttl=3600)
def clean_and_combine_breach_tables():
    """Function to clean and combine data breach tables from multiple sources"""
    
    with st.spinner("Collecting and processing breach data..."):
        # Load Maine data
        df_maine = maine_breach_table()
        
        # Load HHS data
        try:
            df_hhs = pd.read_html(requests.get("https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf").text)[1]
        except:
            df_hhs = pd.DataFrame()
        
        # Load Texas data
        df_tx = breach_report_tx()
        
        # Load Washington data
        df_wa = washington_db()
        
        # Load Hawaii data
        df_hi = hawaii_db()
        
        # Load California data
        try:
            df_ca = pd.read_html(requests.get("https://oag.ca.gov/privacy/databreach/list").text)[0]
        except:
            df_ca = pd.DataFrame()
    
    # Clean each table
    df_maine_clean = clean_maine_data(df_maine)
    df_hhs_clean = clean_hhs_data(df_hhs)
    df_tx_clean = clean_texas_data(df_tx)
    df_wa_clean = clean_washington_data(df_wa)
    df_hi_clean = clean_hawaii_data(df_hi)
    df_ca_clean = clean_california_data(df_ca)
    
    # Combine all cleaned dataframes
    dfs_to_combine = [
        df_maine_clean, 
        df_hhs_clean, 
        df_tx_clean, 
        df_wa_clean, 
        df_hi_clean, 
        df_ca_clean
    ]
    
    # Filter out any None values
    dfs_to_combine = [df for df in dfs_to_combine if df is not None]
    
    # Combine all dataframes
    combined_df = pd.concat(dfs_to_combine, ignore_index=True)
    
    # Final cleaning
    final_df = final_cleaning(combined_df)
    
    return final_df

# Main app
def main():
    # Load data
    try:
        df = clean_and_combine_breach_tables()
        
        if df.empty:
            st.warning("No data was collected. Please check your internet connection and try again.")
            return
        
        # Filter for past 2 weeks
        two_weeks_ago = pd.Timestamp.now() - pd.Timedelta(days=14)
        
        # Filter the dataframe
        filtered_df = df[df['date_reported'] >= two_weeks_ago].copy()
        
        # Display the filtered table
        st.markdown(f"**Showing {len(filtered_df)} breaches reported since {two_weeks_ago.strftime('%Y-%m-%d')}**")
        
        # Format the display
        display_df = filtered_df.copy()
        
        # Rename columns for better display
        display_df = display_df.rename(columns={
            'entity_name': 'Entity Name',
            'date_reported': 'Date Reported',
            'total_affected': 'Total Affected',
            'state_residents_affected': 'State Residents Affected',
            'reporting_state_agency': 'Reporting State/Agency',
            'source_link': 'Source Link'
        })
        
        # Format numbers with commas
        if 'Total Affected' in display_df.columns:
            display_df['Total Affected'] = display_df['Total Affected'].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
            )
        
        if 'State Residents Affected' in display_df.columns:
            display_df['State Residents Affected'] = display_df['State Residents Affected'].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
            )
        
        # Format date
        if 'Date Reported' in display_df.columns:
            display_df['Date Reported'] = display_df['Date Reported'].dt.strftime('%Y-%m-%d')
        
        # Display the table
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Please try refreshing the page.")

if __name__ == "__main__":
    main()

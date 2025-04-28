import pandas as pd
import re
import json
import os

# Additional conference name mappings - handling special cases for conference names and abbreviations
CONFERENCE_MAPPINGS = {
    "IJCNN": "International Joint Conference on Neural Networks",
    "NAACL": "Annual Meeting of the North American Chapter of the Association for Computational Linguistics",
    "ACL": "Annual Meeting of the Association for Computational Linguistics",
    "ICCV": "International Conference on Computer Vision",
    "CVPR": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
    "EMNLP": "Conference on Empirical Methods in Natural Language Processing",
    "ICML": "International Conference on Machine Learning",
    "NeurIPS": "Annual Conference on Neural Information Processing Systems",
    "AICCSA": "ACS/IEEE International Conference on Computer Systems and Applications"
}

def load_config():
    """
    Load configuration file
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def check_excel_sheets(file_path):
    """
    Check worksheets in Excel file
    
    Args:
        file_path: Path to Excel file
        
    Returns:
        list: List of worksheet names
    """
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheets = wb.sheetnames
        wb.close()
        return sheets
    except Exception as e:
        print(f"Failed to check worksheets: {str(e)}")
        return []

def load_data(config):
    """
    Load data from Excel files
    
    Args:
        config: Configuration info containing file paths
        
    Returns:
        tuple: (paper data DataFrame, publication category DataFrame, keywords DataFrame)
    """
    # Load paper information - Note: paper info Excel has no header
    paper_info_path = config['file_paths']['paper_info']
    print(f"Reading paper information file: {paper_info_path}")
    if not os.path.exists(paper_info_path):
        raise FileNotFoundError(f"Paper information file does not exist: {paper_info_path}")
    # Explicitly specify header=None because paper info has no header
    paper_df = pd.read_excel(paper_info_path, header=None)
    
    # Load reference information (publication categories and keywords)
    reference_path = config['file_paths']['reference_info']
    print(f"Reading reference information file: {reference_path}")
    if not os.path.exists(reference_path):
        raise FileNotFoundError(f"Reference information file does not exist: {reference_path}")
    
    # Check worksheetss
    sheets = check_excel_sheets(reference_path)
    
    pub_sheet = config['sheet_names']['publication_category']
    kw_sheet = config['sheet_names']['keywords']
    
    if pub_sheet not in sheets:
        raise ValueError(f"Worksheet does not exist: '{pub_sheet}'. Please modify in config.json or check Excel file.")
    if kw_sheet not in sheets:
        raise ValueError(f"Worksheet does not exist: '{kw_sheet}'. Please modify in config.json or check Excel file.")
    
    publication_category_df = pd.read_excel(
        reference_path, 
        sheet_name=pub_sheet
    )
    keywords_df = pd.read_excel(
        reference_path, 
        sheet_name=kw_sheet
    )
    
    return paper_df, publication_category_df, keywords_df

def prepare_mapping_data(publication_df, keywords_df):
    """
    Prepare mapping data: publication names and keyword dictionaries
    
    Args:
        publication_df: Publication category DataFrame
        keywords_df: Keywords DataFrame
        
    Returns:
        tuple: (publication mapping dictionary, keywords dictionary)
    """
    # We directly return publication_df for first_analysis use
    # Because we need to use both journal name and full name
    
    # Keywords dictionary - with publication full name as key, keyword list as value
    keywords = {}
    
    # Get English keywords from keywords table
    # Check if English keywords column exists
    if 'Full Name of the Journal' in keywords_df.columns and 'keyword-English' in keywords_df.columns:
        print("Found 'English Keywords' column, using it for keyword matching")
        # Use English keywords column
        for _, row in keywords_df.iterrows():
            if not pd.isna(row['Full Name of the Journal']) and not pd.isna(row['keyword-English']):
                journal_name = row['Full Name of the Journal'].strip()
                # Assume keywords are comma-separated
                keyword_list = [kw.strip() for kw in str(row['keyword-English']).split(',') if kw.strip()]
                
                if keyword_list:
                    if journal_name in keywords:
                        # Merge keywords
                        keywords[journal_name].extend(keyword_list)
                    else:
                        keywords[journal_name] = keyword_list
                        
    # If English keywords column not found, use default keywords column
    elif 'Full Name of the Journal' in keywords_df.columns and 'keyword-Chinese' in keywords_df.columns:
        print("'English Keywords' column not found, using 'Keywords' column for matching")
        for _, row in keywords_df.iterrows():
            if not pd.isna(row['Full Name of the Journal']) and not pd.isna(row['keyword-Chinese']):
                journal_name = row['Full Name of the Journal'].strip()
                # Assume keywords are comma-separated
                keyword_list = [kw.strip() for kw in str(row['keyword-Chinese']).split(',') if kw.strip()]
                
                if keyword_list:
                    if journal_name in keywords:
                        # Merge keywords
                        keywords[journal_name].extend(keyword_list)
                    else:
                        keywords[journal_name] = keyword_list
    else:
        print("No keywords column found, will generate keywords based on publication names")
        # If no keywords column found, create default keywords for conference names
        for abbr, fullname in CONFERENCE_MAPPINGS.items():
            if fullname not in keywords:
                keywords[fullname] = [abbr.lower()]  # Use abbreviation as keyword
    
    # Deduplicate keyword lists
    for journal_name in keywords:
        keywords[journal_name] = list(set(keywords[journal_name]))
        
    print(f"Generated keyword dictionary for {len(keywords)} publications")
    
    return publication_df, keywords

def first_analysis(df, publication_mapping):
    """
    First step analysis: Find records containing "Comments" and match them with publication names
    
    Matching logic:
    1. Priority matching with "Full Publication Name", avoiding partial matches
    2. If no match, try matching all-capital English "Publication Name"
    3. Try extracting conference names from patterns like "Accepted at/in/to [conference name]"
    4. If no matches, don't select this paper
    
    Args:
        df: Paper data DataFrame
        publication_mapping: Publication mapping dictionary
        
    Returns:
        DataFrame: Matched records
    """
    matches = []
    
    # Prepare matching data structures
    # Extract publication names and full names from publication_mapping
    journal_fullnames = {}  # Publication name -> Full publication name
    journal_categories = {}  # Full publication name -> Category
    journal_types = {}       # Full publication name -> Type
    journal_levels = {}      # Full publication name -> Level
    
    # Default values for conference types and levels - correctly set based on CCF ranking
    default_conference_types = {}
    default_conference_levels = {}
    
    # CCF-A conferences
    ccf_a_conferences = [
        "International Conference on Computer Vision",  # ICCV
        "IEEE/CVF Conference on Computer Vision and Pattern Recognition",  # CVPR
        "Annual Conference on Neural Information Processing Systems",  # NeurIPS
        "International Conference on Machine Learning",  # ICML
        "Annual Meeting of the Association for Computational Linguistics"  # ACL
    ]
    
    # CCF-B conferences
    ccf_b_conferences = [
        "Conference on Empirical Methods in Natural Language Processing",  # EMNLP
        "Annual Meeting of the North American Chapter of the Association for Computational Linguistics"  # NAACL
    ]
    
    # CCF-C conferences
    ccf_c_conferences = [
        "International Joint Conference on Neural Networks"  # IJCNN
    ]
    
    # Set default conference types and levels
    for conf_name in CONFERENCE_MAPPINGS.values():
        default_conference_types[conf_name] = "Conference"
        
        if conf_name in ccf_a_conferences:
            default_conference_levels[conf_name] = "A"
        elif conf_name in ccf_b_conferences:
            default_conference_levels[conf_name] = "B"
        elif conf_name in ccf_c_conferences:
            default_conference_levels[conf_name] = "C"
        else:
            default_conference_levels[conf_name] = ""  # Unranked conferences shown as empty
    
    # Get publication data from reference info
    from pandas import DataFrame
    if isinstance(publication_mapping, DataFrame):
        # If it's a DataFrame, extract data from it
        # Skip first row, start from second row
        for i, (_, row) in enumerate(publication_mapping.iterrows()):
            # Skip first row
            if i == 0:
                continue
                
            short_name = row['Journal Name'].strip()
            full_name = row['Full Name of the Journal'].strip()
            journal_type = row['Type'].strip() if 'Type' in row and not pd.isna(row['Type']) else "Unknown"
            
            # Ensure level only has A, B, C, others shown as empty
            journal_level = ""
            if 'Level' in row and not pd.isna(row['Level']):
                level = row['Level'].strip()
                if level in ["A", "B", "C"]:
                    journal_level = level
            
            journal_fullnames[short_name] = full_name
            journal_categories[full_name] = full_name  # Use full name as category
            journal_types[full_name] = journal_type    # Record type
            journal_levels[full_name] = journal_level  # Record level
    else:
        # If it's a dictionary, use directly
        journal_fullnames = publication_mapping
        journal_categories = {v: v for v in publication_mapping.values()}
        journal_types = {v: "Unknown" for v in publication_mapping.values()}
        journal_levels = {v: "" for v in publication_mapping.values()}  # Default empty
    
    # Add additional conference name mappings to journal_categories
    for abbr, fullname in CONFERENCE_MAPPINGS.items():
        if fullname not in journal_categories:
            journal_categories[fullname] = fullname
            journal_types[fullname] = default_conference_types.get(fullname, "Conference")
            journal_levels[fullname] = default_conference_levels.get(fullname, "")  # Use our set level
            # Only add if abbreviation not in journal_fullnames
            if abbr not in journal_fullnames:
                journal_fullnames[abbr] = fullname
    
    # Create list of special publications requiring more precise matching
    special_journals = [
        "Artificial Intelligence",
        "Neural Networks",
        "AI"
    ]
    
    # Define helper function for conference name matching
    def is_exact_match(text, journal_name):
        """Check if text exactly matches a conference or journal name"""
        import re
        
        # For special journals, need stricter matching
        if journal_name in special_journals:
            # Try to find exact match pattern, e.g., "Artificial Intelligence"
            # Can be preceded or followed by punctuation, space or brackets
            pattern = r'(?:^|\W)(' + re.escape(journal_name) + r')(?:\W|$)'
            if re.search(pattern, text):
                # Check if matched part is part of a bigger conference/journal name
                # E.g., should not match "International Conference on Artificial Intelligence"
                match = re.search(pattern, text)
                start, end = match.span(1)
                
                # Check if preceded by something that might be part of a conference name
                # Common prefixes like "Conference on", "Journal of", etc.
                prefixes = ["Conference on", "Journal of", "Symposium on", "Workshop on"]
                for prefix in prefixes:
                    if text[max(0, start-len(prefix)-5):start].strip().endswith(prefix):
                        return False  # If preceded by common prefix, might be part of larger conference
                
                return True
            return False
        
        # Special handling for standard matching logic to prevent partial matches
        # E.g., prevent "Neural Networks" from matching "International Joint Conference on Neural Networks"
        if journal_name.lower() in text.lower():
            # General case exact match check
            # Try to recognize complete conference/journal name based on common formats
            # E.g.: Accepted at/in/to [conference name]
            accepted_patterns = [
                r'[Aa]ccepted\s+(?:at|in|to|for)\s+(?:the\s+)?([^,.()]*' + re.escape(journal_name) + r'[^,.()]*)',
                r'[Aa]ccepted\s+(?:by|for)\s+(?:the\s+)?([^,.()]*' + re.escape(journal_name) + r'[^,.()]*)',
                r'[Pp]ublished\s+in\s+(?:the\s+)?([^,.()]*' + re.escape(journal_name) + r'[^,.()]*)',
                r'[Tt]o\s+appear\s+in\s+(?:the\s+)?([^,.()]*' + re.escape(journal_name) + r'[^,.()]*)'
            ]
            
            for pattern in accepted_patterns:
                match = re.search(pattern, text)
                if match:
                    matched_text = match.group(1).strip()
                    # If matched text is exactly the same as journal_name or contains it as a whole
                    if matched_text.lower() == journal_name.lower() or \
                       re.search(r'\b' + re.escape(journal_name) + r'\b', matched_text, re.IGNORECASE):
                        return True
            
            # If no accept/publish patterns found, check for abbreviation in parentheses
            # E.g.: "Neural Networks (NN)" or "International Conference on XXX (ICXXX)"
            abbr_pattern = re.escape(journal_name) + r'\s*\([A-Z]+\)'
            if re.search(abbr_pattern, text, re.IGNORECASE):
                return True
            
            # Check if journal_name appears as standalone word, not part of larger name
            # Use word boundary \b
            if re.search(r'\b' + re.escape(journal_name) + r'\b', text, re.IGNORECASE):
                # Additional check to prevent false matches
                # E.g., "Neural Networks" should not match "International Conference on Neural Networks"
                surrounding_text = text.lower()
                journal_pos = surrounding_text.find(journal_name.lower())
                
                # Check if surrounding text has typical conference name format
                conference_indicators = [
                    "conference on", "symposium on", "workshop on", 
                    "international", "journal of", "transactions on"
                ]
                
                # Check if text before journal_name contains conference indicators
                for indicator in conference_indicators:
                    # Only check text immediately before journal_name
                    pre_text = surrounding_text[max(0, journal_pos-50):journal_pos].strip()
                    if pre_text.endswith(indicator):
                        return False  # Might be part of larger conference name
                
                return True
            
            return False
        
        return False
    
    # Helper function to extract conference name
    def extract_conference_name(text):
        """Extract possible conference names from text"""
        import re
        
        # Find common conference reference patterns
        patterns = [
            # Acceptance status
            r'[Aa]ccepted\s+(?:at|in|to|for)\s+(?:the\s+)?([^,.()]+)',
            r'[Aa]ccepted\s+(?:by|for)\s+(?:the\s+)?([^,.()]+)',
            r'[Pp]ublished\s+in\s+(?:the\s+)?([^,.()]+)',
            r'[Tt]o\s+appear\s+in\s+(?:the\s+)?([^,.()]+)',
            # Publication status
            r'[Tt]o\s+be\s+published\s+in\s+(?:the\s+)?([^,.()]+)',
            # Conference abbreviation in parentheses
            r'(?:[^(]+)\s*\(([A-Z]{2,}(?:\s*[-–—]?\s*\d*)?)\)',
            # Standalone uppercase abbreviation that might be conference name
            r'\b([A-Z]{3,}(?:\s*\d{4})?)\b',
            # Conference abbreviation with year (no space) - new pattern
            r'\b([A-Z]{2,}\d{4})\b',
            # Conference abbreviation with year (with space) - new pattern
            r'\b([A-Z]{2,})\s+\d{4}\b'
        ]
        
        results = []
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                conf_name = match.group(1).strip()
                # Filter out strings that are clearly not conference names
                if conf_name and len(conf_name) > 2 and not conf_name.isdigit():
                    results.append(conf_name)
        
        return results
    
    # Iterate through paper data
    for index, row in df.iterrows():
        # Ensure we can access data correctly
        title = str(row.iloc[0]) if len(row) > 0 else ""
        subject = str(row.iloc[2]) if len(row) > 2 else ""
        url = str(row.iloc[3]) if len(row) > 3 else ""
        
        # Check if subject column contains "Comments"
        if "Comments" in subject:
            matched = False
            matched_publication = ""
            match_type = ""
            
            # 1. First try to match full publication name
            for full_name in journal_categories.keys():
                if is_exact_match(subject, full_name):
                    matched = True
                    matched_publication = full_name
                    match_type = "Exact Full Name"
                    break
            
            # 2. If full name not matched, try matching all-caps publication name
            if not matched:
                for short_name, full_name in journal_fullnames.items():
                    # Check if short name is all uppercase English letters
                    if short_name.isupper() and short_name in subject:
                        # Extra check to ensure it's a standalone abbreviation
                        # Abbreviations are usually in parentheses or appear as standalone words
                        # E.g., (ACL) or ACL 2023
                        if re.search(r'[({\[]?\b' + re.escape(short_name) + r'\b[)}\]]?', subject):
                            matched = True
                            matched_publication = full_name
                            match_type = "Exact Short Name"
                            break
                        # Add new recognition logic: check "CVPR2025" format
                        elif re.search(r'\b' + re.escape(short_name) + r'\d{4}\b', subject):
                            matched = True
                            matched_publication = full_name
                            match_type = "Short Name with Year"
                            break
            
            # 3. Analyze Comments for possible conference information
            if not matched:
                # Extract possible conference names
                conf_names = extract_conference_name(subject)
                for conf_name in conf_names:
                    # Check if there's an exact match for conference name
                    if conf_name in CONFERENCE_MAPPINGS:
                        matched = True
                        matched_publication = CONFERENCE_MAPPINGS[conf_name]
                        match_type = "Conference Name Match"
                        break
                    
                    # Check if conference abbreviation matches
                    # E.g., "IJCNN 2025" should match "IJCNN"
                    for abbr, full_name in CONFERENCE_MAPPINGS.items():
                        # Enhanced matching logic, handling cases where year directly follows abbr
                        # E.g., "CVPR2025" should match "CVPR"
                        if re.search(r'\b' + re.escape(abbr) + r'\b', conf_name, re.IGNORECASE) or \
                           re.search(r'\b' + re.escape(abbr) + r'\d{4}\b', conf_name, re.IGNORECASE) or \
                           conf_name.startswith(abbr):
                            matched = True
                            matched_publication = full_name
                            match_type = "Conference Abbr Match"
                            break
                    
                    if matched:
                        break
            
            # 4. If matched, add to results
            if matched:
                # Get publication type and level
                journal_type = journal_types.get(matched_publication, "Unknown")
                journal_level = journal_levels.get(matched_publication, "")
                
                matches.append({
                    'Title': title,
                    'Subject': subject,
                    'URL': url,
                    'Publication': matched_publication,
                    'Publication_Type': journal_type,
                    'Publication_Level': journal_level,
                    'Match_Type': match_type
                })
    
    result_df = pd.DataFrame(matches)
    # If we have results, add column indicating match type
    if not result_df.empty and 'Match_Type' not in result_df.columns:
        result_df['Match_Type'] = ''
    
    return result_df

def second_analysis(result_df, keywords):
    """
    Second step analysis: Check if title contains keywords corresponding to the publication
    
    Args:
        result_df: DataFrame from first step analysis
        keywords: Keywords dictionary
        
    Returns:
        DataFrame: DataFrame with keyword match information added
    """
    if not result_df.empty:
        result_df['Keywords_Hit'] = ''
        
        for index, row in result_df.iterrows():
            pub = row['Publication']
            if pub in keywords:
                keyword_list = keywords[pub]
                hits = []
                
                # Check if title contains keywords (exact match but case-insensitive)
                title = row['Title']
                for keyword in keyword_list:
                    # Build regex for exact matching, ignoring case
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, title, re.IGNORECASE):
                        hits.append(keyword)
                
                # If there are matched keywords, join them with commas
                if hits:
                    result_df.at[index, 'Keywords_Hit'] = ', '.join(hits)
    
    return result_df

def format_and_display_results(result_df):
    """
    Format and display analysis results
    
    Args:
        result_df: Analysis result DataFrame
    """
    # Rename columns for output
    result_df = result_df.rename(columns={
        'Title': 'Paper Title',
        'Subject': 'Classification',
        'URL': 'Link',
        'Publication': 'Publication Category',
        'Publication_Type': 'Publication Type',
        'Publication_Level': 'Publication Level',
        'Keywords_Hit': 'Keywords Hit',
        'Match_Type': 'Match Type'
    })

    # Set pandas display options
    pd.set_option('display.unicode.ambiguous_as_wide', True)
    pd.set_option('display.unicode.east_asian_width', True)
    pd.set_option('display.width', 150)  # Increase display width
    pd.set_option('display.max_colwidth', 40)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.expand_frame_repr', False)  # Prevent DataFrame from being split into multiple lines

    # Output results
    print("\n" + "="*120)
    print(" "*50 + "Academic Paper Publication Analysis Report")
    print("="*120 + "\n")

    print("【Publication Matching Analysis】Identifying paper publication/acceptance status from Comments info:\n")
    if result_df.empty:
        print("  No matches found")
    else:
        # First step analysis results
        print(f"Found matched records: {len(result_df)}\n")
        
        # Truncate long titles for better display
        display_df = result_df[['Paper Title', 'Publication Category', 'Publication Type', 'Publication Level', 'Match Type']].copy()
        display_df['Paper Title'] = display_df['Paper Title'].apply(lambda x: (x[:35] + '...') if len(x) > 35 else x)
        
        # Use formatted string output to ensure alignment
        print("Paper Title".ljust(40) + "Publication Category".ljust(45) + "Type".ljust(8) + "Level".ljust(10) + "Match Type".ljust(15))
        print("-" * 120)
        
        for idx, row in display_df.iterrows():
            title = row['Paper Title'].ljust(40)
            publication = row['Publication Category'].ljust(45)
            pub_type = row['Publication Type'].ljust(8)
            pub_level = row['Publication Level'].ljust(10)
            match_type = row['Match Type'].ljust(15)
            print(f"{title}{publication}{pub_type}{pub_level}{match_type}")
        
        print("\n" + "-"*120)
        print("\n【Keyword Relevance Analysis】Evaluating paper title relevance to target journal/conference topics:\n")
        
        # Count hit statistics
        total_rows = len(result_df)
        hits_count = result_df['Keywords Hit'].apply(lambda x: len(str(x)) > 0).sum()
        
        print(f"  Total records: {total_rows}, Records with keyword hits: {hits_count}\n")
        
        # Display second step analysis results
        result_with_hits = result_df[result_df['Keywords Hit'].astype(str) != '']
        if len(result_with_hits) > 0:
            hits_df = result_with_hits[['Paper Title', 'Publication Category', 'Publication Type', 'Publication Level', 'Keywords Hit']].copy()
            hits_df['Paper Title'] = hits_df['Paper Title'].apply(lambda x: (x[:35] + '...') if len(x) > 35 else x)
            
            # Use formatted string output
            print("Paper Title".ljust(40) + "Publication Category".ljust(45) + "Type".ljust(8) + "Level".ljust(10) + "Keywords Hit".ljust(15))
            print("-" * 120)
            
            for idx, row in hits_df.iterrows():
                title = row['Paper Title'].ljust(40)
                publication = row['Publication Category'].ljust(45)
                pub_type = row['Publication Type'].ljust(8)
                pub_level = row['Publication Level'].ljust(10)
                keywords = row['Keywords Hit'].ljust(15)
                print(f"{title}{publication}{pub_type}{pub_level}{keywords}")
        else:
            print("  No keyword hits found")
            
    print("\n" + "="*120)

def save_results(result_df, output_path=None):
    """
    Save analysis results to Excel file
    
    Args:
        result_df: Analysis result DataFrame
        output_path: Output file path, defaults to 'analysis_results.xlsx' in current directory
    """
    if result_df.empty:
        print("\nNo results to save.")
        return
        
    # Avoid permission issues by using a filename unlikely to be locked
    if output_path is None:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(os.path.dirname(__file__), f'analysis_results_{timestamp}.xlsx')
    
    # Rename columns for output
    save_df = result_df.rename(columns={
        'Title': 'Paper Title',
        'Subject': 'Classification Info',
        'URL': 'Link',
        'Publication': 'Publication Category',
        'Publication_Type': 'Publication Type',
        'Publication_Level': 'Publication Level',
        'Keywords_Hit': 'Keywords Hit',
        'Match_Type': 'Match Type'
    })
    
    try:
        save_df.to_excel(output_path, index=False)
        print(f"\nAnalysis results saved to: {output_path}")
    except PermissionError:
        # If permission error occurs, try saving to user documents directory
        import pathlib
        user_docs = os.path.join(pathlib.Path.home(), "Documents")
        alt_path = os.path.join(user_docs, f'analysis_results_{timestamp}.xlsx')
        try:
            save_df.to_excel(alt_path, index=False)
            print(f"\nNo write permission to original path, results saved to: {alt_path}")
        except Exception as e:
            print(f"\nFailed to save results: {str(e)}")
            print("Please manually copy results from console output.")
    except Exception as e:
        print(f"\nFailed to save results: {str(e)}")
        print("Please manually copy results from console output.")

def main():
    """
    Main function, program entry point
    """
    # Load configuration
    config = load_config()
    print("Configuration loaded successfully!")
    
    # Load data
    try:
        paper_df, publication_df, keywords_df = load_data(config)
        print("Data loaded successfully!")
        print(f"Paper data rows: {len(paper_df)}")
    except Exception as e:
        print(f"Data loading failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Prepare mapping data
    try:
        publication_mapping, keywords = prepare_mapping_data(publication_df, keywords_df)
        print("Mapping data prepared successfully!")
    except Exception as e:
        print(f"Mapping data preparation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # First step analysis
    try:
        result_df = first_analysis(paper_df, publication_mapping)
        print(f"First step analysis completed, found {len(result_df)} matching records")
    except Exception as e:
        print(f"First step analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Second step analysis
    try:
        result_df = second_analysis(result_df, keywords)
        print("Second step analysis completed!")
    except Exception as e:
        print(f"Second step analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Display results
    format_and_display_results(result_df)
    
    # Save results
    save_results(result_df)

if __name__ == "__main__":
    main() 
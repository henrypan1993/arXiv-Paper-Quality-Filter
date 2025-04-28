# arXiv Academic Paper Analysis and Filtering Tool

[English](./README.en.md) | [中文](./README.md)

This is a comprehensive workflow tool for academic paper analysis, focusing on identifying and filtering AI papers from arXiv that have been accepted or published in top-tier journals/conferences. The entire workflow includes:

1. **Data Collection**: Automatically scrape paper information from arXiv's AI category using WinRobot360 RPA
2. **Paper Filtering**: Analyze the Comments field to identify papers that have been accepted or published in prestigious venues
3. **Quality Assessment**: Filter and grade papers based on the [international academic journal directory](https://www.ccf.org.cn/Academic_Evaluation/AI/) recommended by the China Computer Federation (CCF)
4. **Keyword Matching**: Apply personal keywords to further tag high-quality papers in specific research domains

This tool is ideal for researchers looking to quickly discover the latest high-quality AI research, especially papers that have been accepted by top conferences/journals but not yet formally published.

## Test Data

We will provide a test data package that includes:
1. Sample arXiv paper information
2. CCF recommended international academic journal reference list
3. Example keyword configuration

You can use this test data to familiarize yourself with the tool's functionality and workflow.

## Main Features

The tool performs two main analysis steps:

1. **First Analysis**: Find records containing "Comments" in the paper data and match them with publication names
   - Search for records containing "Comments" in the third column (Column C - description information)
   - **Matching Logic**:
     - Prioritize checking if the description contains the "Full Name of the Journal" from reference information
     - If no match, try matching all-caps English "Journal Name"
     - Try matching special formats like "CVPR2025" for conference name abbreviations
     - Try extracting conference names from patterns like "Accepted at/in/to [conference name]"
     - If no match is found, the paper is not selected
   - Record the matching result and match type (exact full name/exact abbreviation/abbreviation with year/conference name match/conference abbreviation match)

2. **Second Analysis**: Check if the title of matched records contains specific keywords
   - Get English keywords from the "keywords" worksheet
   - Check if the paper title contains these keywords (exact match but case-insensitive)
   - If matched, display the hit keywords in the results

## Configuration

The program uses a JSON format configuration file (`config.json`) to store file paths and worksheet names:

```json
{
    "file_paths": {
        "paper_info": "C:\\Users\\panhe\\Desktop\\论文信息.xlsx",
        "reference_info": "C:\\Users\\panhe\\Desktop\\中国计算机学会推荐国际学术刊物&会议.xlsx"
    },
    "sheet_names": {
        "publication_category": "category",
        "keywords": "keyword"
    }
}
```

You can modify the paths and worksheet names in the configuration file according to your needs.

## Usage

1. Make sure you have installed Python environment and necessary libraries (pandas, openpyxl)
2. Modify the `config.json` file to ensure the file paths are correct
3. Run the script:

```bash
python arXiv-Paper-Quality-Filter.py
```

## Output Results

The program displays analysis results in the console and saves complete results to an Excel file:

1. First analysis results: Shows matched papers, corresponding publication categories, and match types
2. Second analysis results: Shows papers with titles containing specific keywords
3. All results are saved in a timestamped `analysis_results_[timestamp].xlsx` file

## Data Requirements

1. **Paper Information Excel File**:
   - **No header**, data starts from the first row
   - Column A - Paper title
   - Column B - Author information
   - Column C - Description information (may contain "Comments" keyword)
   - Column D - PDF URL

2. **Reference Information Excel File**:
   - Has headers
   - Must contain "Journal Name" and "Full Name of the Journal" columns
   - All-caps English names in the "Journal Name" column are used for second priority matching
   - The "keywords" worksheet should have "keyword-English" column for the second analysis step

## Conference Mapping Configuration

The program includes built-in mappings for conference names and abbreviations to identify conference names more accurately:

```python
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
```

You can add more conference mappings in the code.

## Detailed Matching Logic

1. **Priority 1: Exact Full Name Match**
   - Check if the paper description (Column C) contains any "Full Name of the Journal" from reference information
   - Matching is case-insensitive but must be a complete match
   - Match type: `Exact Full Name`

2. **Priority 2: Journal Name Match**
   - Only executed if priority 1 matching fails
   - Only matches all-caps English journal names (e.g., "TPAMI", "IJCV")
   - Matching is case-sensitive and must be an exact match
   - Match type: `Exact Short Name`

3. **Priority 3: Abbreviated Name with Year Match**
   - Only executed if the previous two matching methods fail
   - Matches formats like "CVPR2025" (no space)
   - Match type: `Short Name with Year`

4. **Priority 4: Conference Name/Abbreviation Match**
   - Try to extract possible conference names from the text
   - Match the extracted names with the built-in conference mapping relationships
   - Match type: `Conference Name Match` or `Conference Abbr Match`

5. **No Match Cases**
   - If the paper description does not contain "Comments"
   - If no conference or journal name is matched in the paper description

## Keyword Matching Details

In the second analysis step, keyword matching has the following characteristics:
- Uses the "keyword-English" column in the "keywords" worksheet for matching
- Uses exact word boundary matching to ensure only complete words are matched, not parts of words
- Matching is case-insensitive, so "Neural" can match "neural" or "NEURAL"
- Multiple keywords are separated by commas

## Troubleshooting

If you encounter the following issues, try the corresponding solutions:

1. **Worksheet not found**: Check the actual worksheet names in the Excel file and update the configuration in `config.json`
2. **Column name mismatch**: View the actual column names in the Excel file and modify the column name references in the code
3. **File path error**: Ensure the file path is correct, note the use of double backslashes or raw strings in Windows paths
4. **Data format issues**: Ensure the paper information Excel has no header, while the reference information Excel has headers
5. **Conference recognition issues**: If certain conference names cannot be recognized, add corresponding mappings in the `CONFERENCE_MAPPINGS` in the code

## Recent Updates

- Enhanced the recognition of conference abbreviation formats, now able to recognize formats like "CVPR2025" without spaces
- Improved keyword matching logic, using the "keyword-English" column for exact matching
- Fixed issues with recognizing some conferences

## Data Source

This tool uses paper data automatically scraped from arXiv's AI category using WinRobot360 RPA. The specific scraping process is as follows:

- Uses WinRobot360 RPA automation tool for data collection
- The robot automatically visits the arXiv website and retrieves the latest paper information in the AI category
- Extracts data including paper title, authors, abstract, Comments information, and PDF links
- Data is automatically saved in Excel format for use by this analysis tool

To use or modify the scraping robot, you can access it via the following link: [arXiv Paper Scraping Robot](https://api.winrobot360.com/redirect/robot/share?inviteKey=4fa722bd79b12b1f)

If you need to modify the web pages to scrape or change the scraping quantity, you can open the WinRobot360 RPA software and edit the workflow.

## Environment Requirements

- Python 3.6+
- pandas
- openpyxl 
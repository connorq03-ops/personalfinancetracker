"""
Budget Excel/CSV Parser for importing user budget files.
Handles multi-section budget formats with categories and amounts in paired columns.
"""
import pandas as pd
from datetime import date


class BudgetParser:
    """Parse budget files (Excel/CSV) with flexible column mapping."""
    
    # Default column mappings for the user's budget format
    # Format: (category_column, amount_column, group_name)
    # Excel format (0-indexed): C=2, D=3, H=7, I=8, M=12, N=13, R=17, S=18
    EXCEL_SECTIONS = [
        (2, 3, 'Fixed Expenses'),      # Columns C/D - Key expenses
        (7, 8, 'Credit Cards'),         # Columns H/I - CC payments
        (12, 13, 'Food & Entertainment'),  # Columns M/N - Food/Entertainment
        (17, 18, 'Savings & Goals'),    # Columns R/S - Savings/Goals
    ]
    
    # CSV format has different column indices due to how Excel exports
    # CSV: Column 1/2 for Fixed, 6/7 for CC, 11/12 for Food, 16/17 for Savings
    CSV_SECTIONS = [
        (1, 2, 'Fixed Expenses'),       # Columns B/C in CSV
        (6, 7, 'Credit Cards'),         # Columns G/H in CSV
        (11, 12, 'Food & Entertainment'),  # Columns L/M in CSV
        (16, 17, 'Savings & Goals'),    # Columns Q/R in CSV
    ]
    
    DEFAULT_SECTIONS = EXCEL_SECTIONS
    
    def __init__(self):
        self.sections = self.DEFAULT_SECTIONS
    
    def parse_excel(self, file_path, header_row=7):
        """
        Parse an Excel budget file.
        
        Args:
            file_path: Path to the Excel file
            header_row: Row number (0-indexed) where headers are located
            
        Returns:
            dict with budget items grouped by section
        """
        df = pd.read_excel(file_path, header=None)
        return self._parse_dataframe(df, header_row)
    
    def parse_csv(self, file_path, header_row=7):
        """
        Parse a CSV budget file.
        
        Args:
            file_path: Path to the CSV file
            header_row: Row number (0-indexed) where headers are located
            
        Returns:
            dict with budget items grouped by section
        """
        df = pd.read_csv(file_path, header=None)
        # Use CSV-specific column mappings
        self.sections = self.CSV_SECTIONS
        return self._parse_dataframe(df, header_row)
    
    def parse_file_object(self, file_obj, filename, header_row=7):
        """
        Parse a file object (for web uploads).
        
        Args:
            file_obj: File-like object
            filename: Original filename to determine format
            header_row: Row number (0-indexed) where headers are located
            
        Returns:
            dict with budget items grouped by section
        """
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file_obj, header=None)
            self.sections = self.EXCEL_SECTIONS
        else:
            df = pd.read_csv(file_obj, header=None)
            self.sections = self.CSV_SECTIONS
        
        return self._parse_dataframe(df, header_row)
    
    def _parse_dataframe(self, df, header_row):
        """
        Parse a DataFrame with the multi-section budget format.
        
        Args:
            df: pandas DataFrame
            header_row: Row number where headers are located
            
        Returns:
            dict with budget items grouped by section
        """
        result = {
            'sections': {},
            'all_items': [],
            'total_budget': 0,
            'parse_errors': []
        }
        
        # Start parsing from the row after headers
        data_start = header_row + 1
        
        for cat_col, amt_col, group_name in self.sections:
            section_items = []
            
            # Iterate through rows starting after header
            for idx in range(data_start, len(df)):
                try:
                    category = df.iloc[idx, cat_col]
                    amount = df.iloc[idx, amt_col]
                    
                    # Skip empty rows
                    if pd.isna(category) or str(category).strip() == '':
                        continue
                    
                    # Clean up category name
                    category = str(category).strip()
                    
                    # Parse amount
                    if pd.isna(amount):
                        amount = 0
                    else:
                        try:
                            # Handle string amounts with $ or commas
                            if isinstance(amount, str):
                                amount = amount.replace('$', '').replace(',', '').strip()
                            amount = float(amount)
                        except (ValueError, TypeError):
                            result['parse_errors'].append(
                                f"Could not parse amount for '{category}': {amount}"
                            )
                            amount = 0
                    
                    # Skip zero amounts unless it's a valid category
                    if amount > 0 or category.lower() not in ['nan', 'none', '']:
                        item = {
                            'category': category,
                            'amount': round(amount, 2),
                            'group': group_name
                        }
                        section_items.append(item)
                        result['all_items'].append(item)
                        result['total_budget'] += amount
                        
                except Exception as e:
                    result['parse_errors'].append(f"Error parsing row {idx}: {str(e)}")
            
            result['sections'][group_name] = section_items
        
        result['total_budget'] = round(result['total_budget'], 2)
        return result
    
    def get_category_mapping(self, parsed_budget, existing_categories):
        """
        Create a mapping between parsed budget categories and existing database categories.
        
        Args:
            parsed_budget: Result from parse_* methods
            existing_categories: List of existing category dicts with 'id' and 'name'
            
        Returns:
            dict mapping budget category names to existing category IDs or None
        """
        # Create lowercase lookup for existing categories
        existing_lookup = {c['name'].lower(): c for c in existing_categories}
        
        mapping = {}
        for item in parsed_budget['all_items']:
            cat_name = item['category']
            cat_lower = cat_name.lower()
            
            # Try exact match first
            if cat_lower in existing_lookup:
                mapping[cat_name] = {
                    'matched': True,
                    'category_id': existing_lookup[cat_lower]['id'],
                    'category_name': existing_lookup[cat_lower]['name']
                }
            else:
                # Try partial matching
                matched = None
                for existing_name, existing_cat in existing_lookup.items():
                    if cat_lower in existing_name or existing_name in cat_lower:
                        matched = existing_cat
                        break
                
                if matched:
                    mapping[cat_name] = {
                        'matched': True,
                        'category_id': matched['id'],
                        'category_name': matched['name'],
                        'partial_match': True
                    }
                else:
                    mapping[cat_name] = {
                        'matched': False,
                        'category_id': None,
                        'category_name': None,
                        'suggested_group': item['group']
                    }
        
        return mapping


def preview_budget_file(file_path):
    """Utility function to preview a budget file structure."""
    parser = BudgetParser()
    
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        result = parser.parse_excel(file_path)
    else:
        result = parser.parse_csv(file_path)
    
    print(f"Total Budget: ${result['total_budget']:,.2f}")
    print(f"Parse Errors: {len(result['parse_errors'])}")
    print()
    
    for section_name, items in result['sections'].items():
        if items:
            section_total = sum(i['amount'] for i in items)
            print(f"=== {section_name} (${section_total:,.2f}) ===")
            for item in items:
                if item['amount'] > 0:
                    print(f"  {item['category']}: ${item['amount']:,.2f}")
            print()
    
    if result['parse_errors']:
        print("Errors:")
        for err in result['parse_errors']:
            print(f"  - {err}")
    
    return result


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        preview_budget_file(sys.argv[1])
    else:
        print("Usage: python budget_parser.py <budget_file.xlsx>")

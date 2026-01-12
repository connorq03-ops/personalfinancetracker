"""
Bank of America PDF Statement Parser.
Extracts transactions from Bank of America checking/savings account statements.
"""
import re
from datetime import datetime
from dateutil import parser as date_parser
import pdfplumber


class BoAParser:
    """Parser for Bank of America PDF statements."""
    
    def __init__(self):
        self.source = 'Bank of America'
        
        # Regex patterns for BoA statements
        # Date at start of line: MM/DD/YY
        self.date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(.+)')
        # Amount pattern - can be positive or negative, with optional comma
        self.amount_pattern = re.compile(r'(-?[\d,]+\.\d{2})$')
        # Amount on its own line (continuation from previous)
        self.amount_only_pattern = re.compile(r'^(-?[\d,]+\.\d{2})$')
    
    def parse_statement(self, pdf_path, year=None):
        """
        Parse a Bank of America PDF statement.
        
        Args:
            pdf_path: Path to the PDF file
            year: Year for the statement (defaults to current year)
            
        Returns:
            List of transaction dictionaries
        """
        if year is None:
            year = datetime.now().year
        
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                transactions = self._parse_all_text(full_text, year)
        except Exception as e:
            print(f"Error parsing PDF {pdf_path}: {e}")
            return []
        
        return transactions
    
    def _parse_all_text(self, text, year):
        """Parse all text from the PDF for transactions."""
        transactions = []
        lines = text.split('\n')
        
        in_deposits = False
        in_withdrawals = False
        current_transaction = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Detect section starts
            if 'deposits and other additions' in line.lower():
                in_deposits = True
                in_withdrawals = False
                continue
            elif 'withdrawals and other subtractions' in line.lower():
                in_deposits = False
                in_withdrawals = True
                continue
            
            # End sections
            if 'total deposits' in line.lower() or 'total withdrawals' in line.lower():
                in_deposits = False
                in_withdrawals = False
                # Save any pending transaction
                if current_transaction and not current_transaction.get('partial'):
                    transactions.append(current_transaction)
                current_transaction = None
                continue
            
            # Skip non-transaction lines
            if any(skip in line.lower() for skip in [
                'date description amount', 'continued on', 'page ', 'account #',
                'ending balance', 'beginning balance', 'account security',
                'check your security', 'mobile banking', 'scan the code',
                'braille and large print'
            ]):
                continue
            
            if not (in_deposits or in_withdrawals):
                continue
            
            # Check if this line starts with a date
            date_match = self.date_pattern.match(line)
            
            if date_match:
                # Save previous transaction if exists
                if current_transaction and not current_transaction.get('partial'):
                    transactions.append(current_transaction)
                
                date_str = date_match.group(1)
                rest_of_line = date_match.group(2)
                
                # Check if amount is on this line
                amount_match = self.amount_pattern.search(rest_of_line)
                
                if amount_match:
                    amount_str = amount_match.group(1)
                    description = rest_of_line[:amount_match.start()].strip()
                    
                    # Create transaction
                    current_transaction = self._create_transaction(
                        date_str, description, amount_str, year, in_withdrawals
                    )
                else:
                    # Amount might be on next line, store partial transaction
                    current_transaction = {
                        'date_str': date_str,
                        'description': rest_of_line,
                        'is_withdrawal': in_withdrawals,
                        'partial': True
                    }
            else:
                # Check if this is an amount-only line (continuation)
                amount_only_match = self.amount_only_pattern.match(line)
                
                if amount_only_match and current_transaction and current_transaction.get('partial'):
                    amount_str = amount_only_match.group(1)
                    current_transaction = self._create_transaction(
                        current_transaction['date_str'],
                        current_transaction['description'],
                        amount_str,
                        year,
                        current_transaction['is_withdrawal']
                    )
                elif current_transaction and current_transaction.get('partial'):
                    # This might be continuation of description, check for amount at end
                    amount_match = self.amount_pattern.search(line)
                    if amount_match:
                        amount_str = amount_match.group(1)
                        extra_desc = line[:amount_match.start()].strip()
                        full_desc = current_transaction['description'] + ' ' + extra_desc
                        current_transaction = self._create_transaction(
                            current_transaction['date_str'],
                            full_desc,
                            amount_str,
                            year,
                            current_transaction['is_withdrawal']
                        )
                    else:
                        # Just append to description
                        current_transaction['description'] += ' ' + line
        
        # Don't forget the last transaction
        if current_transaction and not current_transaction.get('partial'):
            transactions.append(current_transaction)
        
        return transactions
    
    def _finalize_transaction(self, date_str, desc_parts, year, is_withdrawal):
        """Create transaction from accumulated parts."""
        full_text = ' '.join(desc_parts)
        
        # Extract amount from end
        amount_match = self.amount_pattern.search(full_text)
        if not amount_match:
            return None
        
        amount_str = amount_match.group(1)
        description = full_text[:amount_match.start()].strip()
        
        return self._create_transaction(date_str, description, amount_str, year, is_withdrawal)
    
    def _create_transaction(self, date_str, description, amount_str, year, is_withdrawal=False):
        """Create a transaction dictionary."""
        try:
            # Parse date
            date = date_parser.parse(date_str)
            if date.year < 2000:
                date = date.replace(year=year)
            
            # Parse amount
            amount = float(amount_str.replace(',', ''))
            if is_withdrawal and amount > 0:
                amount = -amount
            
            # Clean description
            description = self._clean_description(description)
            
            return {
                'date': date.date(),
                'description': description,
                'amount': amount,
                'source': self.source,
                'raw_category': None
            }
        except Exception as e:
            print(f"Error creating transaction: {e}")
            return None
    
    def _clean_description(self, description):
        """Clean up transaction description."""
        # Remove extra whitespace
        description = ' '.join(description.split())
        # Remove common prefixes
        prefixes = ['MOBILE PURCHASE', 'PURCHASE', 'CHECKCARD', 'POS']
        for prefix in prefixes:
            if description.upper().startswith(prefix):
                description = description[len(prefix):].strip()
        return description

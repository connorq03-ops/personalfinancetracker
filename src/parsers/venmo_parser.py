"""
Venmo CSV transaction parser.
"""
import pandas as pd


class VenmoParser:
    """Parser for Venmo CSV exports."""
    
    def __init__(self):
        self.source = 'Venmo'
    
    def parse_csv(self, csv_path):
        """
        Parse a Venmo CSV file.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Venmo CSVs often have extra header rows
            df = pd.read_csv(csv_path, skiprows=2)
            return self._process_dataframe(df)
        except Exception as e:
            print(f"Error parsing CSV {csv_path}: {e}")
            return []
    
    def _process_dataframe(self, df):
        """Process dataframe into transaction list."""
        transactions = []
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        for _, row in df.iterrows():
            try:
                # Parse date
                date_col = 'datetime' if 'datetime' in df.columns else 'date'
                date_val = row.get(date_col)
                if pd.isna(date_val):
                    continue
                
                date = pd.to_datetime(date_val).date()
                
                # Build description from note and recipient
                note = str(row.get('note', '')) if not pd.isna(row.get('note')) else ''
                to_user = str(row.get('to', '')) if not pd.isna(row.get('to')) else ''
                from_user = str(row.get('from', '')) if not pd.isna(row.get('from')) else ''
                
                if to_user:
                    description = f"To {to_user}: {note}"
                elif from_user:
                    description = f"From {from_user}: {note}"
                else:
                    description = note or 'Venmo Transaction'
                
                # Parse amount
                amount_val = row.get('amount (total)')
                if pd.isna(amount_val):
                    amount_val = row.get('amount')
                
                if pd.isna(amount_val):
                    continue
                
                if isinstance(amount_val, str):
                    # Remove currency symbols and handle negative
                    amount_str = amount_val.replace('$', '').replace(',', '').strip()
                    amount = float(amount_str)
                else:
                    amount = float(amount_val)
                
                transactions.append({
                    'date': date,
                    'description': description.strip(),
                    'amount': amount,
                    'source': self.source,
                    'raw_category': None
                })
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        return transactions

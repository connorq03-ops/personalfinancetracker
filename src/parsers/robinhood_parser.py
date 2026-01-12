"""
Robinhood Credit Card CSV transaction parser.
"""
import pandas as pd
from datetime import datetime


class RobinhoodParser:
    """Parser for Robinhood Credit Card CSV exports."""
    
    def __init__(self):
        self.source = 'Robinhood CC'
    
    def parse_csv(self, csv_path):
        """
        Parse a Robinhood CC CSV file.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of transaction dictionaries
        """
        try:
            df = pd.read_csv(csv_path)
            return self._process_dataframe(df)
        except Exception as e:
            print(f"Error parsing CSV {csv_path}: {e}")
            return []
    
    def _process_dataframe(self, df):
        """Process dataframe into transaction list."""
        transactions = []
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        print(f"Robinhood CSV columns: {list(df.columns)}")
        
        for _, row in df.iterrows():
            try:
                # Parse date
                date_val = row.get('date')
                if pd.isna(date_val):
                    continue
                
                if isinstance(date_val, str):
                    date = pd.to_datetime(date_val).date()
                else:
                    date = date_val.date() if hasattr(date_val, 'date') else date_val
                
                # Get merchant (primary identifier)
                merchant = ''
                if 'merchant' in df.columns and not pd.isna(row.get('merchant')):
                    merchant = str(row['merchant']).strip()
                
                # Get description (secondary info)
                desc = ''
                if 'description' in df.columns and not pd.isna(row.get('description')):
                    desc = str(row['description']).strip()
                
                # Combine merchant and description for full description
                if merchant and desc:
                    description = f"{merchant} - {desc}"
                elif merchant:
                    description = merchant
                elif desc:
                    description = desc
                else:
                    # Fallback to type
                    txn_type = row.get('type', '')
                    description = str(txn_type) if not pd.isna(txn_type) else 'Unknown'
                
                # Parse amount
                amount_val = row.get('amount')
                if pd.isna(amount_val):
                    continue
                
                if isinstance(amount_val, str):
                    amount = float(amount_val.replace('$', '').replace(',', ''))
                else:
                    amount = float(amount_val)
                
                # Skip zero amounts
                if amount == 0:
                    continue
                
                transactions.append({
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'source': self.source,
                    'raw_category': row.get('type', None)
                })
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        
        return transactions

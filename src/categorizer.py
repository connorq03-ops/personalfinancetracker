"""
ML-based transaction categorization using TF-IDF + Naive Bayes.
"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


class TransactionCategorizer:
    """
    Hybrid categorizer combining rule-based and ML approaches.
    Uses rules for common patterns, ML for everything else.
    """
    
    def __init__(self, model_path=None):
        self.model_path = model_path or 'categorizer_model.joblib'
        self.pipeline = None
        self.is_trained = False
        self.rule_categorizer = RuleBasedCategorizer()
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self):
        """Load trained model from disk if exists."""
        if os.path.exists(self.model_path):
            try:
                self.pipeline = joblib.load(self.model_path)
                self.is_trained = True
            except Exception:
                self.is_trained = False
    
    def train(self, descriptions, categories):
        """
        Train the ML model on transaction descriptions.
        
        Args:
            descriptions: List of transaction descriptions
            categories: List of corresponding category names
        """
        if len(descriptions) < 10:
            return False
        
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                lowercase=True,
                max_features=5000,
                ngram_range=(1, 2),
                stop_words='english'
            )),
            ('classifier', MultinomialNB(alpha=0.1))
        ])
        
        self.pipeline.fit(descriptions, categories)
        self.is_trained = True
        
        # Save model
        joblib.dump(self.pipeline, self.model_path)
        return True
    
    def predict(self, description):
        """
        Predict category for a transaction description.
        Uses rules first, falls back to ML if trained.
        """
        # Try rule-based first
        rule_prediction = self.rule_categorizer.predict(description)
        if rule_prediction != 'Uncategorized':
            return rule_prediction
        
        # Try ML if trained
        if self.is_trained and self.pipeline:
            try:
                return self.pipeline.predict([description])[0]
            except Exception:
                pass
        
        return 'Uncategorized'
    
    def predict_with_confidence(self, description):
        """Predict category with confidence score."""
        category = self.predict(description)
        confidence = 0.9 if self.rule_categorizer.predict(description) != 'Uncategorized' else 0.7
        
        if self.is_trained and self.pipeline:
            try:
                proba = self.pipeline.predict_proba([description])[0]
                confidence = max(proba)
            except Exception:
                pass
        
        return category, confidence


class RuleBasedCategorizer:
    """
    Rule-based categorizer using keyword matching.
    Fast and reliable for common transaction patterns.
    """
    
    def __init__(self):
        self.rules = {
            'Income': [
                'dir dep', 'direct dep', 'payroll', 'salary', 'paycheck',
                'ach credit', 'deposit'
            ],
            
            'Coffee': [
                'starbucks', 'coffee', 'dunkin', 'peets', 'blue bottle',
                'la colombe', 'houndstooth'
            ],
            
            'Groceries': [
                'h-e-b', 'heb', 'whole foods', 'trader joe', 'grocery',
                'central market', 'kroger', 'safeway', 'publix', 'costco'
            ],
            
            'Eating Out': [
                'doordash', 'uber eats', 'grubhub', 'postmates',
                'tst*', 'sq *', 'restaurant', 'cafe', 'diner', 'grill',
                'kitchen', 'taco', 'pizza', 'burger', 'sushi', 'thai',
                'chinese', 'mexican', 'chipotle', 'panera'
            ],
            
            'Uber/Lyft': [
                'uber *trip', 'uber trip', 'lyft', 'lime*ride'
            ],
            
            'Subscriptions': [
                'netflix', 'spotify', 'hulu', 'amazon prime',
                'apple.com/bill', 'disney+', 'hbo', 'youtube premium',
                'microsoft*ultimate', 'subscription'
            ],
            
            'Utilities': [
                'city of austin', 'electric', 'water bill', 'utility',
                'comcast', 'spectrum', 'xfinity', 'one gas', 'atmos'
            ],
            
            'Rent': [
                'rent', 'apartment', 'lease', 'property mgmt'
            ],
            
            'Investments': [
                'fid bkg svc', 'moneyline', 'fidelity', 'vanguard',
                'schwab', 'acorns', 'etrade', 'td ameritrade'
            ],
            
            'Credit Card Payment': [
                'chase credit crd', 'discover', 'capital one', 'amex',
                'credit card payment', 'cc payment'
            ],
            
            'Venmo': ['venmo'],
            'PayPal': ['paypal'],
            
            'Shopping': [
                'amazon', 'target', 'walmart', 'best buy', 'home depot',
                'lowes', 'ikea', 'amz*'
            ],
            
            'Gas': [
                'shell', 'chevron', 'exxon', 'gas station', 'fuel',
                'bp ', 'mobil', 'valero'
            ],
            
            'Tolls': ['hctra', 'ez tag', 'toll'],
            
            'Healthcare': [
                'pharmacy', 'cvs', 'walgreens', 'doctor', 'medical',
                'hospital', 'clinic', 'dental'
            ],
            
            'Entertainment': [
                'movie', 'theater', 'concert', 'ticket', 'amc',
                'nintendo', 'playstation', 'xbox', 'steam'
            ],
            
            'Transfer': [
                'transfer', 'zelle'
            ],
            
            'Wire Transfer': [
                'wire type:', 'wire transfer'
            ],
            
            'ATM': [
                'atm', 'withdrwl', 'withdrawal', 'bkofamerica atm'
            ],
            
            'Robinhood CC': [
                'robinhood card des:payment'
            ],
            
            'Chase CC': [
                'chase credit crd'
            ],
            
            'Loan Payment': [
                'upgrade, inc', 'sst ', 'loan pmt', 'tally'
            ],
            
            'Mortgage': [
                'truist mortg', 'mortgage', 'mtgpmt'
            ],
            
            'Phone/Internet': [
                'att des:payment', 'at&t', 't-mobile', 'sprint', 'comcast'
            ],
            
            'Natural Gas': [
                'one gas', 'atmos energy', 'centerpoint'
            ],
            
            'Alcohol': [
                'little woodrow', 'bar', 'pub', 'liquor', 'beer', 'wine'
            ],
            
            'Gym': [
                'ymca', 'gym', 'fitness', 'planet fitness', 'equinox'
            ],
            
            'Travel': [
                'airline', 'southwest', 'delta', 'united', 'american air',
                'hotel', 'airbnb', 'marriott', 'hilton'
            ],
        }
    
    def predict(self, description):
        """Predict category based on keyword rules."""
        desc_lower = description.lower()
        
        for category, keywords in self.rules.items():
            if any(keyword in desc_lower for keyword in keywords):
                return category
        
        return 'Uncategorized'


# Singleton instance
_categorizer = None


def get_categorizer():
    """Get the singleton categorizer instance."""
    global _categorizer
    if _categorizer is None:
        _categorizer = TransactionCategorizer()
    return _categorizer

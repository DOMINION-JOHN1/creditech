import json
import time
import fitz  # PyMuPDF
import pdfplumber
import re
from datetime import datetime

from pathlib import Path

static_path = Path(config.STATIC_DIRECTORY)
if not static_path.exists():
    raise RuntimeError(f"Missing static directory: {static_path}. Please create it.")

class BankStatementAnalyzer:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.start_time = time.time()
        self.metadata = {
            'accuracy_score': 100,
            'fraud_indicators': [],
            'processing_duration': 0
        }
        self.result = {
            'identity': {},
            'credit_transactions': [],
            'debit_transactions': [],
            'metadata': self.metadata
        }

    def analyze_pdf_integrity(self):
        """Check PDF for signs of tampering"""
        doc = fitz.open(self.pdf_path)
        
        # Check for hidden layers or annotations
        for page in doc:
            if page.get_annots():
                self.metadata['fraud_indicators'].append("Hidden annotations detected")
                self.metadata['accuracy_score'] -= 15

        # Check creation/modification dates
        creation_date = doc.metadata.get('creationDate')
        mod_date = doc.metadata.get('modDate')
        if creation_date and mod_date and creation_date != mod_date:
            self.metadata['fraud_indicators'].append("PDF modification date mismatch")
            self.metadata['accuracy_score'] -= 20

        # Check for multiple font inconsistencies
        with pdfplumber.open(self.pdf_path) as pdf:
            fonts = set()
            for page in pdf.pages:
                chars = page.chars
                for char in chars:
                    fonts.add(char['fontname'])
            
            if len(fonts) > 5:  # Threshold for font variations
                self.metadata['fraud_indicators'].append("Multiple font inconsistencies")
                self.metadata['accuracy_score'] -= 25

        doc.close()

    def extract_identity_info(self, text):
        """Extract account holder information using regex patterns"""
        patterns = {
            'name': r"Account Name:\s*(.+)",
            'number': r"Account Number:\s*(\d+)",
            'bank': r"Bank Name:\s*(.+)",
            'period': r"Statement Period:\s*(.+)"
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                self.result['identity'][field] = match.group(1).strip()
            else:
                self.metadata['fraud_indicators'].append(f"Missing {field.replace('_', ' ')}")
                self.metadata['accuracy_score'] -= 5

    def extract_transactions(self, text):
        """Extract credit and debit transactions with enhanced pattern matching"""
        transaction_pattern = r"""
            (\d{2}-\w{3}-\d{4})  # Date
            \s+(.*?)             # Description
            \s+(-?\d{1,3}(?:,\d{3})*\.\d{2})  # Amount
        """
        
        for match in re.finditer(transaction_pattern, text, re.VERBOSE):
            date_str, description, amount = match.groups()
            amount = float(amount.replace(',', ''))
            
            transaction = {
                'date': datetime.strptime(date_str, "%d-%b-%Y").isoformat(),
                'description': description.strip(),
                'amount': amount
            }

            if amount > 0:
                self.result['credit_transactions'].append(transaction)
            else:
                self.result['debit_transactions'].append(transaction)

        # Transaction consistency check
        if not self.result['credit_transactions'] and not self.result['debit_transactions']:
            self.metadata['fraud_indicators'].append("No transactions detected")
            self.metadata['accuracy_score'] -= 30

    def analyze(self):
        """Main analysis workflow"""
        self.analyze_pdf_integrity()
        
        with pdfplumber.open(self.pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() for page in pdf.pages)
            
            self.extract_identity_info(full_text)
            self.extract_transactions(full_text)

        # Finalize metadata
        self.metadata['processing_duration'] = round(time.time() - self.start_time, 2)
        self.metadata['accuracy_score'] = max(0, self.metadata['accuracy_score'])
        
        return self.result

# Usage Example
if __name__ == "__main__":
    analyzer = BankStatementAnalyzer("AC_JOHN DOMINION ELEOJO_FEBRUARY 2025_641R010130868_FullStmt.pdf")
    result = analyzer.analyze()
    
    print(json.dumps(result, indent=2))
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/scouting_engine.py
# 📝 ዓላማ፦ Product & Seller Bulk Seeding Engine (Optimized & Pruned)
# ✅ የተፈቱ ችግሮች፦ Redundant AI Data Generation (Handled in growth_agent), DB Leaks
# 📅 ቀን፦ 2026-06-23
# ============================================================

import csv
import io
import random
import logging
from django.contrib.auth.models import User
from django.db import transaction, connection
from django.utils import timezone
from .models import Product, Category, SiteRegistry, ProductTranslation

logger = logging.getLogger(__name__)


class ProductScoutingEngine:
    """
    ምርቶችን እና የባለቤት መገለጫዎችን ከCSV ፋይል በጅምላ የሚያስገባ ፈጣን ሞተር
    """
    
    REQUIRED_CSV_COLUMNS = ['name', 'price', 'description']
    
    def __init__(self, user, site: SiteRegistry = None):
        self.user = user
        self.site = site
        self.import_errors = []
        self.imported_count = 0
        self.updated_count = 0
    
    def process_csv(self, csv_file):
        """CSV ፋይልን ሂደት በማድረግ ምርቶችን በከፍተኛ ፍጥነት ያስገባል"""
        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            if not self._validate_headers(reader.fieldnames):
                return {
                    'success': False,
                    'error': 'Invalid CSV headers. Required: ' + ', '.join(self.REQUIRED_CSV_COLUMNS),
                    'imported': 0,
                    'errors': self.import_errors
                }
            
            products_to_create = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    product_data = self._parse_product_row(row)
                    if product_data:
                        products_to_create.append(product_data)
                except Exception as e:
                    self.import_errors.append(f"Row {row_num}: {str(e)}")
            
            # በጅምላ በአንድ ግብይት (Transaction Atomic) መጻፍ
            with transaction.atomic():
                for product_data in products_to_create:
                    self._create_product(product_data)
                    self.imported_count += 1
            
            return {
                'success': True,
                'imported': self.imported_count,
                'errors': self.import_errors,
                'total_rows': len(products_to_create)
            }
            
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'imported': 0,
                'errors': self.import_errors
            }
        finally:
            # የዳታቤዝ ግንኙነትን በጊዜ መዝጋት
            connection.close()
    
    def _validate_headers(self, headers):
        if not headers:
            return False
        return all(col in headers for col in self.REQUIRED_CSV_COLUMNS)
    
    def _parse_product_row(self, row):
        name = row.get('name', '').strip()
        if not name:
            raise ValueError("Product name is required")
        
        try:
            price = float(row.get('price', 0))
            if price <= 0:
                raise ValueError("Price must be greater than 0")
        except ValueError:
            raise ValueError("Invalid price format")
        
        description = row.get('description', '').strip()
        if not description:
            description = f"{name} - Quality product"
        
        category_name = row.get('category', '').strip()
        
        return {
            'name': name,
            'price': price,
            'description': description,
            'category': category_name
        }
    
    def _create_product(self, product_data):
        category = None
        if product_data.get('category'):
            category, _ = Category.objects.get_or_create(
                name=product_data['category'],
                defaults={'description': f"{product_data['category']} products"}
            )
        
        product = Product.objects.create(
            title=product_data['name'],
            price=product_data['price'],
            description=product_data['description'],
            category=category,
            seller=self.user,
            site=self.site,
            is_active=True,
            market_value_status='Active'
        )
        
        combined = f"{product_data['name']} ||| {product_data['description']}"
        ProductTranslation.objects.get_or_create(
            product=product,
            defaults={'en': combined, 'am': combined}
        )
        return product
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/scouting_engine.py
# 📝 ለውጥ፦ Product & Customer Scouting Engine
# 📅 ቀን፦ 2026-06-21
# ============================================================

import csv
import io
import random
import uuid
import logging
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from .models import Product, Category, SiteRegistry, ProductTranslation

logger = logging.getLogger(__name__)


class ProductScoutingEngine:
    """
    ምርቶችን ከCSV ለማስገባት እና ለማስተዳደር ሞተር
    """
    
    REQUIRED_CSV_COLUMNS = ['name', 'price', 'description']
    OPTIONAL_CSV_COLUMNS = ['category', 'stock', 'sku', 'image_url']
    
    def __init__(self, user, site: SiteRegistry = None):
        self.user = user
        self.site = site
        self.import_errors = []
        self.imported_count = 0
        self.updated_count = 0
    
    def process_csv(self, csv_file, update_existing=False):
        """CSV ፋይልን ሂደት በማድረግ ምርቶችን ወደ ዳታቤዝ ያስገባል"""
        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            # የCSV አምዶችን አረጋግጥ
            if not self._validate_headers(reader.fieldnames):
                return {
                    'success': False,
                    'error': 'Invalid CSV headers. Required: ' + ', '.join(self.REQUIRED_CSV_COLUMNS),
                    'imported': 0,
                    'updated': 0,
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
                    logger.warning(f"CSV import error at row {row_num}: {e}")
            
            with transaction.atomic():
                for product_data in products_to_create:
                    self._create_product(product_data)
                    self.imported_count += 1
            
            return {
                'success': True,
                'imported': self.imported_count,
                'updated': self.updated_count,
                'errors': self.import_errors,
                'total_rows': len(products_to_create)
            }
            
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'imported': 0,
                'updated': 0,
                'errors': self.import_errors
            }
    
    def _validate_headers(self, headers):
        """የCSV አምዶች ትክክል መሆናቸውን ያረጋግጣል"""
        if not headers:
            return False
        return all(col in headers for col in self.REQUIRED_CSV_COLUMNS)
    
    def _parse_product_row(self, row):
        """አንድ ረድፍ ምርት ወደ መዋቅር ይቀይራል"""
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
        stock = int(row.get('stock', 0)) if row.get('stock', '').strip() else random.randint(10, 100)
        sku = row.get('sku', '').strip()
        image_url = row.get('image_url', '').strip()
        
        return {
            'name': name,
            'price': price,
            'description': description,
            'category': category_name,
            'stock': stock,
            'sku': sku,
            'image_url': image_url
        }
    
    def _create_product(self, product_data):
        """አዲስ ምርት በዳታቤዝ ውስጥ ይፈጥራል"""
        category = None
        if product_data.get('category'):
            category, _ = Category.objects.get_or_create(
                name=product_data['category'],
                defaults={'description': f"{product_data['category']} products"}
            )
        
        sku = product_data.get('sku', '')
        if not sku:
            sku = f"SKU-{random.randint(10000, 99999)}-{int(timezone.now().timestamp())}"
        
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
        
        # ትርጉም ፍጠር
        combined = f"{product_data['name']} ||| {product_data['description']}"
        ProductTranslation.objects.get_or_create(
            product=product,
            defaults={'en': combined, 'am': combined}
        )
        
        logger.info(f"✅ Product created: {product.title} (ID: {product.id})")
        return product
    
    def generate_sample_csv(self):
        """ለመጠቀም ናሙና CSV ይፈጥራል"""
        sample_data = [
            ['name', 'price', 'description', 'category', 'stock', 'sku', 'image_url'],
            ['የኢትዮጵያ ቡና', '450.00', 'ጥሩ ጥራት ያለው የኢትዮጵያ ቡና', 'ቡና', '100', 'COF-001', ''],
            ['የእጅ ስራ ሸክላ', '1200.00', 'በእጅ የተሰራ የኢትዮጵያ ባህላዊ ሸክላ', 'ባህላዊ', '50', 'HAN-001', ''],
            ['የባህላዊ ልብስ', '2500.00', 'ባህላዊ የኢትዮጵያ ልብስ', 'ልብስ', '30', 'CLO-001', ''],
        ]
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(sample_data)
        return output.getvalue()


class AIDataGenerator:
    """AI በመጠቀም እውነተኛ የሚመስሉ ምርቶችን ያመነጫል"""
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
    
    def generate_products(self, count=10):
        """AI በመጠቀም ምርቶችን ያመነጫል"""
        # ይህ ከ AI ጋር ይገናኛል
        from .growth_agent import ask_ethafri_ceo
        
        site_context = ""
        if self.site:
            site_context = f"""
            Site Niche: {self.site.niche}
            Target Market: {self.site.target_market}
            Keywords: {self.site.primary_keywords}
            """
        
        prompt = f"""
        Generate {count} realistic product listings for an e-commerce site.
        {site_context}
        
        Return ONLY a JSON array:
        [
            {{
                "title": "Product Name",
                "description": "Product description",
                "price": 100.00,
                "category": "Category Name",
                "stock": 50
            }}
        ]
        """
        
        response = ask_ethafri_ceo(prompt, pool_type="coding")
        if not response:
            return []
        
        if isinstance(response, dict):
            products = response.get('products', [])
        else:
            try:
                import json
                import re
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    products = json.loads(match.group(0))
                else:
                    products = []
            except Exception:
                products = []
        
        return products
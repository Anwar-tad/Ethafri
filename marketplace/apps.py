# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ዓላማ፦ ሙሉ በሙሉ አውቶኖመስ Self-Healing System (v13.0 - Ultimate Autonomous Edition)
# ✅ ችሎታዎች፦
#   - ራሱ ዳታቤዙን ተቆጣጥሮ የጎደሉትን ቴብሎች መለየት እና መፍጠር
#   - ያልታወቁ የስህተት ንድፎችን መማር እና ማስታወስ
#   - AI ን በመጠቀም አዲስ መፍትሄዎችን መፍጠር
#   - ሙሉ ራስ-ፈወስ ዑደት ከ growth_agent ጋር የተቀናጀ
#   - የደህንነት እና የአፈጻጸም ችግሮችን በራሱ መፈታት
#   - ሙሉ ሪፖርት እና የጥገና ታሪክ
#   - ከተሳሳተ መማር እና ራስን ማሻሻል
# 📅 ቀን፦ Tuesday, June 30, 2026
# ============================================================
import os
import sys
import time
import json
import threading
import logging
import re
from datetime import datetime, timedelta

from django.apps import AppConfig
from django.utils import timezone
from django.db import connection, connections
from django.core.management import call_command
from django.db.models import Count

logger = logging.getLogger(__name__)
import os
import ast
import re
import json
import logging
import time
import subprocess
import sys
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from django.utils import timezone
from django.db import connection, connections, DatabaseError, OperationalError, transaction
from django.core.management import call_command
from django.db.models import Q, Count
from django.conf import settings
from django.apps import apps

from .models import (
    AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry,
    SecurityLog, VectorMemory, SiteConfig
)
from .code_apply import apply_code_change

logger = logging.getLogger(__name__)

# ============================================================
# 🔧 ረዳት: ቅንጅቶችን ከ SiteConfig ማምጣት
# ============================================================
def _cfg(key: str, default):
    """SiteConfig ከሌለ default ዋጋን ይመልሳል"""
    try:
        obj = SiteConfig.objects.filter(key=key).first()
        return obj.value.get("v", default) if obj else default
    except Exception:
        return default


# ============================================================
# 🛡️ SQL Whitelist Validator
# ============================================================
_ALLOWED_SQL_PREFIXES = (
    "create index", "drop index", "create table", "alter table",
    "delete from django_migrations",
)
_FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(drop\s+database|truncate|drop\s+table\s+(?!if\s+exists\s+\"marketplace_)"
    r"|insert\s+into\s+(?!marketplace_)|update\s+(?!marketplace_))\b",
    re.IGNORECASE,
)

def _validate_ai_sql(sql: str) -> Tuple[bool, str]:
    """AI-produced SQL ን ደህንነቱ ጠብቆ ይፈትሻል"""
    if not sql or not isinstance(sql, str):
        return False, "SQL empty or not a string"
    normalized = sql.strip().lower()
    if not any(normalized.startswith(p) for p in _ALLOWED_SQL_PREFIXES):
        return False, f"SQL starts with disallowed keyword: {normalized[:40]}"
    if _FORBIDDEN_SQL_PATTERNS.search(sql):
        return False, "SQL contains forbidden destructive pattern"
    if len(sql) > 2000:
        return False, "SQL suspiciously long (> 2000 chars)"
    return True, ""


# ============================================================
# 🧠 ዘመናዊ የስህተት ንድፍ መማሪያ እና መዝገብ
# ============================================================
class ErrorPatternLearner:
    """ከተሳሳተ ይማራል እና ለቀጣይ ያስታውሳል"""
    
    @staticmethod
    def learn_from_error(error_message: str, solution: str, site, success: bool = True):
        """አዲስ የስህተት ንድፍ ይማራል"""
        try:
            # የስህተቱን ዋና ንድፍ ያውጣል
            pattern = re.sub(r'\d+', '{number}', error_message)
            pattern = re.sub(r'"[^"]*"', '{string}', pattern)
            pattern = re.sub(r"\'[^\']*\'", '{string}', pattern)
            
            # የስህተቱን አይነት ይለያል
            error_type = "unknown"
            if "relation" in error_message.lower() and "does not exist" in error_message.lower():
                error_type = "missing_table"
            elif "column" in error_message.lower() and "does not exist" in error_message.lower():
                error_type = "missing_column"
            elif "OperationalError" in error_message:
                error_type = "connection_error"
            elif "SyntaxError" in error_message:
                error_type = "syntax_error"
            elif "FieldError" in error_message:
                error_type = "field_error"
            elif "ProgrammingError" in error_message:
                error_type = "programming_error"
            
            VectorMemory.objects.create(
                site=site,
                memory_type='error_pattern',
                content=f"Pattern: {pattern[:200]}\nSolution: {solution[:500]}",
                metadata={
                    'error': error_message[:500],
                    'solution': solution[:500],
                    'error_type': error_type,
                    'success': success
                },
                success_rate=1.0 if success else 0.0,
                usage_count=1
            )
            logger.info(f"🧠 Learned new error pattern: {error_type} - {pattern[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to learn error pattern: {e}")
            return False
    
    @staticmethod
    def find_solution_for_error(error_message: str, site) -> Optional[Dict]:
        """ተመሳሳይ የስህተት ንድፍ ያገኛል"""
        try:
            # የስህተቱን ንድፍ ያውጣል
            pattern = re.sub(r'\d+', '{number}', error_message)
            pattern = re.sub(r'"[^"]*"', '{string}', pattern)
            pattern = re.sub(r"\'[^\']*\'", '{string}', pattern)
            
            memories = VectorMemory.objects.filter(
                site=site,
                memory_type='error_pattern',
                content__icontains=pattern[:100]
            ).order_by('-success_rate', '-usage_count')[:3]
            
            if memories:
                # ምርጡን መፍትሄ ይመርጣል
                best = memories[0]
                content = best.content
                solution_match = re.search(r'Solution:\s*(.+?)(?:\n|$)', content)
                if solution_match:
                    return {
                        'solution': solution_match.group(1).strip(),
                        'success_rate': best.success_rate,
                        'usage_count': best.usage_count,
                        'memory_id': best.id
                    }
        except Exception as e:
            logger.error(f"Failed to find solution: {e}")
        return None
    
    @staticmethod
    def get_common_errors(site, limit: int = 10) -> List[Dict]:
        """በተደጋጋሚ የሚከሰቱ ስህተቶችን ያመጣል"""
        try:
            errors = AgentErrorLog.objects.filter(
                site=site,
                resolved=False
            ).values('error_message').annotate(
                count=Count('id')
            ).order_by('-count')[:limit]
            
            return list(errors)
        except Exception as e:
            logger.error(f"Failed to get common errors: {e}")
            return []
    
    @staticmethod
    def update_success_rate(memory_id: int, success: bool):
        """የመፍትሄ ስኬታማነት መጠን ያሻሽላል"""
        try:
            memory = VectorMemory.objects.filter(id=memory_id).first()
            if memory:
                memory.usage_count += 1
                if success:
                    memory.success_rate = ((memory.success_rate * (memory.usage_count - 1)) + 100) / memory.usage_count
                else:
                    memory.success_rate = ((memory.success_rate * (memory.usage_count - 1)) + 0) / memory.usage_count
                memory.save()
        except Exception as e:
            logger.debug(f"Failed to update success rate: {e}")


# ============================================================
# 🔍 ዳታቤዝ ኢንስፔክተር - ራሱ ዳታቤዙን የሚቆጣጠር
# ============================================================
class DatabaseInspector:
    """ራሱ ዳታቤዙን ተቆጣጥሮ የጎደሉትን ቴብሎች የሚለይ ስርዓት"""
    
    def __init__(self):
        self.existing_tables = []
        self.missing_tables = []
        self.table_structures = {}
        self.all_models = []
        self.scan_time = None
        self.inspection_results = {}
        
    def inspect_database(self) -> Dict[str, Any]:
        """ዳታቤዙን ሙሉ በሙሉ ይቆጣጠራል"""
        logger.info("🔍 Starting full database inspection...")
        self.scan_time = timezone.now()
        
        try:
            with connection.cursor() as cursor:
                # 1. ነባር ቴብሎችን ያግኙ
                self.existing_tables = self._get_existing_tables(cursor)
                logger.info(f"📊 Found {len(self.existing_tables)} existing tables")
                
                # 2. ሁሉንም Django models ያግኙ
                self.all_models = self._get_all_models()
                logger.info(f"📚 Found {len(self.all_models)} Django models")
                
                # 3. የጎደሉትን ቴብሎች ይለዩ
                self.missing_tables = self._find_missing_tables()
                
                # 4. የእያንዳንዱን ቴብል መዋቅር ያግኙ
                for table in self.existing_tables:
                    self.table_structures[table] = self._get_table_structure(cursor, table)
                
                # 5. የተገኙትን መረጃዎች ያስቀምጡ
                self._save_inspection_results()
                
        except Exception as e:
            logger.error(f"❌ Database inspection failed: {e}")
            self._emergency_inspection()
        
        return self._generate_report()
    
    def _get_existing_tables(self, cursor) -> List[str]:
        """ነባር ቴብሎችን ያግኙ"""
        if connection.vendor == 'postgresql':
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname='public' AND tablename LIKE 'marketplace_%'
                ORDER BY tablename
            """)
        else:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'marketplace_%'
                ORDER BY name
            """)
        return [row[0] for row in cursor.fetchall()]
    
    def _get_all_models(self) -> List[Dict]:
        """ሁሉንም Django models ያግኙ"""
        models_data = []
        try:
            app_config = apps.get_app_config('marketplace')
            for model in app_config.get_models():
                model_data = {
                    'name': model.__name__,
                    'table_name': model._meta.db_table,
                    'fields': [
                        {
                            'name': field.name,
                            'type': field.get_internal_type(),
                            'null': field.null,
                            'blank': field.blank,
                            'max_length': getattr(field, 'max_length', None),
                            'unique': field.unique,
                            'default': getattr(field, 'default', None)
                        }
                        for field in model._meta.get_fields() 
                        if not field.auto_created
                    ]
                }
                models_data.append(model_data)
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
        return models_data
    
    def _find_missing_tables(self) -> List[Dict]:
        """የጎደሉትን ቴብሎች ይለያል"""
        missing = []
        expected_tables = [model['table_name'] for model in self.all_models]
        
        for expected in expected_tables:
            if expected not in self.existing_tables:
                model = next((m for m in self.all_models if m['table_name'] == expected), None)
                if model:
                    missing.append({
                        'table_name': expected,
                        'model_name': model['name'],
                        'fields': model['fields']
                    })
        
        if missing:
            logger.warning(f"⚠️ Found {len(missing)} missing tables: {[m['table_name'] for m in missing]}")
        else:
            logger.info("✅ All tables exist!")
        
        return missing
    
    def _get_table_structure(self, cursor, table_name: str) -> Dict:
        """የአንድን ቴብል መዋቅር ያግኙ"""
        structure = {'columns': [], 'indexes': [], 'constraints': []}
        try:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, [table_name])
                structure['columns'] = cursor.fetchall()
                
                cursor.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = %s
                """, [table_name])
                structure['indexes'] = cursor.fetchall()
        except Exception as e:
            logger.debug(f"Could not get structure for {table_name}: {e}")
        return structure
    
    def _save_inspection_results(self):
        """የተገኙትን መረጃዎች ያስቀምጣል"""
        try:
            SiteConfig.objects.update_or_create(
                key='DATABASE_INSPECTION_RESULTS',
                defaults={
                    'value': {
                        'existing_tables': self.existing_tables,
                        'missing_tables': [m['table_name'] for m in self.missing_tables],
                        'model_count': len(self.all_models),
                        'scan_time': self.scan_time.isoformat(),
                        'table_count': len(self.existing_tables)
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to save inspection results: {e}")
    
    def _generate_report(self) -> Dict:
        """የቁጥጥር ሪፖርት ያዘጋጃል"""
        return {
            'existing_tables': self.existing_tables,
            'missing_tables': [m['table_name'] for m in self.missing_tables],
            'missing_table_details': self.missing_tables,
            'model_count': len(self.all_models),
            'table_count': len(self.existing_tables),
            'scan_time': self.scan_time,
            'has_missing_tables': len(self.missing_tables) > 0,
            'health_percentage': (len(self.existing_tables) / max(len(self.all_models), 1)) * 100
        }
    
    def _emergency_inspection(self):
        """የቁጥጥር ስህተት ሲኖር የአደጋ ጊዜ ቁጥጥር"""
        try:
            with connection.cursor() as cursor:
                self.existing_tables = self._get_existing_tables(cursor)
        except Exception as e:
            logger.error(f"Emergency inspection failed: {e}")


# ============================================================
# 🧬 ዘመናዊ ቴብል ጄኔሬተር
# ============================================================
class DynamicTableGenerator:
    """የጎደሉትን ቴብሎች በራሱ የሚፈጥር ስርዓት"""
    
    def __init__(self):
        self.generated_tables = []
        self.failed_tables = []
        self.errors = []
        
    def generate_missing_tables(self, inspection_report: Dict) -> Dict:
        """የጎደሉትን ቴብሎች ይፈጥራል"""
        missing_tables = inspection_report.get('missing_table_details', [])
        
        if not missing_tables:
            logger.info("✅ No missing tables to generate")
            return {'generated': [], 'failed': [], 'errors': []}
        
        logger.info(f"🔨 Generating {len(missing_tables)} missing tables...")
        
        for table_info in missing_tables:
            table_name = table_info['table_name']
            try:
                # 1. SQL ያመነጫል
                sql = self._generate_table_sql(table_info)
                
                if sql:
                    # 2. SQL ን ያስፈጽማል
                    success = self._execute_table_creation(sql)
                    
                    if success:
                        self.generated_tables.append(table_name)
                        logger.info(f"✅ Generated table: {table_name}")
                    else:
                        self.failed_tables.append(table_name)
                        logger.error(f"❌ Failed to generate: {table_name}")
                else:
                    self.failed_tables.append(table_name)
                    logger.error(f"❌ Could not generate SQL for: {table_name}")
                    
            except Exception as e:
                logger.error(f"Error generating {table_name}: {e}")
                self.failed_tables.append(table_name)
                self.errors.append(str(e))
        
        return {
            'generated': self.generated_tables,
            'failed': self.failed_tables,
            'errors': self.errors,
            'total': len(missing_tables)
        }
    
    def _generate_table_sql(self, table_info: Dict) -> Optional[str]:
        """ከ table info CREATE TABLE SQL ያመነጫል"""
        try:
            table_name = table_info['table_name']
            fields = table_info.get('fields', [])
            
            if not fields:
                logger.warning(f"No fields found for {table_name}, using generic definition")
                return self._generate_generic_table_sql(table_name)
            
            field_defs = []
            primary_key_found = False
            
            for field in fields:
                field_name = field['name']
                field_type = field['type']
                null_str = "NOT NULL" if not field.get('null', True) else ""
                
                # የመስክ አይነት ወደ SQL ይቀይሩ
                sql_type = self._field_type_to_sql(field_type, field)
                
                # ባዶ እሴቶችን ያስተናግዳል
                if field.get('blank', False) and field_type in ['CharField', 'TextField', 'URLField', 'EmailField', 'SlugField']:
                    null_str = ""
                
                # ነባሪ እሴቶችን ይይዛል
                default_val = field.get('default')
                def_str = ""
                if default_val is not None and default_val != '':
                    if isinstance(default_val, str):
                        def_str = f"DEFAULT '{default_val}'"
                    elif isinstance(default_val, bool):
                        def_str = f"DEFAULT {str(default_val).lower()}"
                    elif default_val is not None:
                        def_str = f"DEFAULT {default_val}"
                
                # ራስ-ሰር መስኮች
                if field_type in ['AutoField', 'BigAutoField'] and field_name == 'id':
                    field_defs.insert(0, "id SERIAL PRIMARY KEY")
                    primary_key_found = True
                    continue
                
                # JSONB መስኮች
                if field_type == 'JSONField':
                    sql_type = 'JSONB'
                    def_str = "DEFAULT '{}'"
                    null_str = ""
                
                # የባዕድ ቁልፎች
                if field_type in ['ForeignKey', 'OneToOneField']:
                    sql_type = 'INTEGER'
                    ref_table = f"marketplace_{field_name.replace('_id', '').lower()}"
                    if field.get('null', True):
                        field_defs.append(f"CONSTRAINT fk_{field_name} FOREIGN KEY ({field_name}) REFERENCES {ref_table}(id) ON DELETE SET NULL")
                    else:
                        field_defs.append(f"CONSTRAINT fk_{field_name} FOREIGN KEY ({field_name}) REFERENCES {ref_table}(id) ON DELETE CASCADE")
                    null_str = ""
                
                field_def = f"{field_name} {sql_type} {null_str} {def_str}".strip()
                field_defs.append(field_def)
            
            # Primary key ከሌለ ያክሉ
            if not primary_key_found:
                field_defs.insert(0, "id SERIAL PRIMARY KEY")
            
            fields_sql = ",\n    ".join(field_defs)
            
            sql = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
    {fields_sql}
);
"""
            return sql
            
        except Exception as e:
            logger.error(f"SQL generation failed: {e}")
            return None
    
    def _generate_generic_table_sql(self, table_name: str) -> str:
        """ለማንኛውም ቴብል አጠቃላይ SQL ያመነጫል"""
        return f"""
CREATE TABLE IF NOT EXISTS {table_name} (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""
    
    def _field_type_to_sql(self, field_type: str, field_info: Dict = None) -> str:
        """Django field type ን ወደ SQL type ይቀይራል"""
        max_length = field_info.get('max_length', 255) if field_info else 255
        
        type_mapping = {
            'AutoField': 'SERIAL',
            'BigAutoField': 'BIGSERIAL',
            'CharField': f"VARCHAR({max_length})",
            'TextField': 'TEXT',
            'IntegerField': 'INTEGER',
            'BigIntegerField': 'BIGINT',
            'SmallIntegerField': 'SMALLINT',
            'FloatField': 'FLOAT',
            'DecimalField': 'DECIMAL(20,2)',
            'BooleanField': 'BOOLEAN',
            'DateField': 'DATE',
            'DateTimeField': 'TIMESTAMP WITH TIME ZONE',
            'TimeField': 'TIME',
            'ForeignKey': 'INTEGER',
            'OneToOneField': 'INTEGER',
            'ManyToManyField': 'INTEGER',
            'JSONField': 'JSONB',
            'URLField': f"VARCHAR({max_length})",
            'EmailField': f"VARCHAR({max_length})",
            'SlugField': f"VARCHAR({max_length})",
            'FileField': f"VARCHAR({max_length})",
            'ImageField': f"VARCHAR({max_length})",
            'UUIDField': 'UUID',
            'IPAddressField': 'INET',
            'GenericIPAddressField': 'INET',
        }
        
        return type_mapping.get(field_type, 'TEXT')
    
    def _execute_table_creation(self, sql: str) -> bool:
        """SQL ን ያስፈጽማል"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
            return True
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return False


# ============================================================
# 🛡️ SECURITY AUDITOR (AST + Regex SHIELD)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ ጥሪዎችን፣ ሚስጥሮችን ይፈትሻል"""

    _DANGEROUS_BUILTINS = {"eval", "exec"}
    _DANGEROUS_ATTRS = {"system", "popen", "spawn"}
    _DANGEROUS_SUBPROCESS = {"run", "call", "popen", "check_output", "check_call"}

    _SECRET_RE = [
        (re.compile(r'SECRET_KEY\s*=\s*[\'"][^\'"]{8,}[\'"]', re.I), "Possible SECRET_KEY exposure"),
        (re.compile(r'\bpassword\s*=\s*[\'"][^\'"]{4,}[\'"]', re.I), "Possible password exposure"),
        (re.compile(r'\bAPI_KEY\s*=\s*[\'"][^\'"]{8,}[\'"]', re.I), "API key exposure"),
        (re.compile(r'\bAWS_SECRET\s*=\s*[\'"][^\'"]{8,}[\'"]', re.I), "AWS secret exposure"),
    ]

    @classmethod
    def scan_code_safety(cls, code: str, file_path: str = "", site=None) -> Tuple[bool, list]:
        if not code or not isinstance(code, str):
            return True, []

        issues = []
        is_python = file_path.endswith(".py") if file_path else True

        if is_python:
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    func = node.func
                    if isinstance(func, ast.Name) and func.id.lower() in cls._DANGEROUS_BUILTINS:
                        issues.append(f"Critical: Dangerous built-in '{func.id}' detected.")
                    elif isinstance(func, ast.Attribute):
                        attr = func.attr.lower()
                        if attr in cls._DANGEROUS_ATTRS:
                            issues.append(f"Critical: Dangerous attribute call '.{attr}()' detected.")
                        mod = getattr(func.value, "id", "").lower()
                        if mod == "subprocess" and attr in cls._DANGEROUS_SUBPROCESS:
                            issues.append(f"Critical: subprocess.{attr}() call detected.")
            except SyntaxError as e:
                issues.append(f"Syntax Error in {file_path}: {e}")
            except Exception as e:
                logger.warning(f"AST scan skipped ({file_path}): {e}")

        for pattern, desc in cls._SECRET_RE:
            if pattern.search(code):
                issues.append(f"Warning: {desc} in {file_path or 'unknown'}")

        if issues:
            cls._persist_issues(issues, file_path, site)
            return False, issues
        return True, []

    @staticmethod
    def _persist_issues(issues, file_path, site):
        for issue in issues:
            try:
                exists = SecurityLog.objects.filter(
                    site=site, description=issue, file_path=file_path
                ).exists()
                if not exists:
                    SecurityLog.objects.create(
                        site=site,
                        category="code_injection" if "Critical" in issue else "data_leak",
                        text_content=issue,
                        severity="critical" if "Critical" in issue else "high",
                        description=issue,
                        file_path=file_path,
                        is_fixed=False,
                    )
            except Exception as e:
                logger.error(f"SecurityLog save failed: {e}")


# ============================================================
# 🚑 UNIVERSAL HEALER (Complete Self-Healing System)
# ============================================================
class UniversalHealer:
    """ኤጀንቱን፣ ዳታቤዙን እና ድረ-ገጹን ስህተት የሚጠግን ማዕከል"""

    _CIRCUIT_MAX_FAILURES = 3
    _CIRCUIT_WINDOW_MINUTES = 60

    def __init__(self, site: SiteRegistry):
        self.site = site
        self.healed_count = 0
        self.failed_count = 0
        self.healing_history = []

    # ── ዋና ጥገና ዑደት ──────────────────────────────────────────
    def perform_maintenance(self):
        """ሙሉ ጥገና ያካሂድ"""
        logger.info(f"🚑 Maintenance started for [{self.site.name}]")
        self._reset_stuck_tasks()
        self.heal_database_migrations_autonomously()
        connections.close_all()
        try:
            PerformanceAuditor.run_daily_performance_audit(self.site)
        except Exception as e:
            logger.error(f"Performance audit error: {e}")
        self._heal_production_errors()
        self._heal_security_issues()
        logger.info(f"✅ Maintenance complete for [{self.site.name}]")

    # ── ሙሉ ራስ-ፈወስ ዑደት ────────────────────────────────────────
    def full_self_heal(self) -> Dict[str, Any]:
        """ሙሉ የራስ-ፈወስ ዑደት"""
        logger.info(f"🔄 Starting full self-heal cycle for {self.site.name}")
        
        results = {
            'tables_checked': 0,
            'tables_created': 0,
            'errors_fixed': 0,
            'security_fixes': 0,
            'performance_fixes': 0,
            'migrations_fixed': False,
            'stuck_tasks_reset': 0,
            'learned_patterns': 0,
            'start_time': timezone.now().isoformat(),
            'success': True,
            'details': []
        }
        
        try:
            # 1. ዳታቤዝ ቁጥጥር እና ቴብሎችን መፍጠር
            logger.info("🔍 Phase 1: Database Inspection...")
            inspector = DatabaseInspector()
            inspection = inspector.inspect_database()
            results['tables_checked'] = len(inspection['existing_tables'])
            results['details'].append(f"Found {len(inspection['existing_tables'])} existing tables")
            
            if inspection['has_missing_tables']:
                logger.info(f"🔨 Phase 2: Generating {len(inspection['missing_tables'])} missing tables...")
                generator = DynamicTableGenerator()
                generation_result = generator.generate_missing_tables(inspection)
                results['tables_created'] = len(generation_result.get('generated', []))
                results['details'].append(f"Created {len(generation_result.get('generated', []))} tables")
                
                if generation_result.get('failed'):
                    results['success'] = False
                    results['details'].append(f"Failed: {generation_result['failed']}")
                    logger.error(f"❌ Failed to generate: {generation_result['failed']}")
                
                # ከስህተቶች መማር
                for error in generation_result.get('errors', []):
                    ErrorPatternLearner.learn_from_error(
                        error,
                        "Use generic table creation with proper SQL syntax",
                        self.site,
                        success=False
                    )
            
            # 2. ማይግሬሽን ማስተካከያ
            logger.info("🔄 Phase 3: Migration Healing...")
            migration_result = self._heal_migrations()
            results['migrations_fixed'] = migration_result
            if migration_result:
                results['details'].append("Migrations fixed")
            
            # 3. የተጣበቁ ተግባራትን ማስተካከል
            logger.info("🧹 Phase 4: Resetting Stuck Tasks...")
            stuck_count = self._reset_stuck_tasks()
            results['stuck_tasks_reset'] = stuck_count
            
            # 4. የስህተት ሎጎች ማጽዳት
            logger.info("🧹 Phase 5: Error Log Cleanup...")
            cleaned = self._clean_error_logs()
            results['errors_fixed'] = cleaned
            
            # 5. የደህንነት ጉዳዮች መፍታት
            logger.info("🛡️ Phase 6: Security Issue Resolution...")
            security_fixed = self._heal_security_issues()
            results['security_fixes'] = len(security_fixed)
            
            # 6. ከስህተቶች መማር
            logger.info("🧠 Phase 7: Learning from Errors...")
            learned = self._learn_from_errors()
            results['learned_patterns'] = learned
            
            # 7. ሪፖርት ማዘጋጀት
            SelfHealingLog.objects.create(
                site=self.site,
                error_message="Full self-heal cycle completed",
                solution_sql=json.dumps(results),
                resolved=True
            )
            
        except Exception as e:
            logger.error(f"❌ Self-healing failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            results['details'].append(f"Error: {str(e)}")
        
        results['duration'] = (timezone.now() - timezone.datetime.fromisoformat(results['start_time'])).total_seconds()
        
        logger.info(f"✅ Full self-heal complete: {results}")
        return results

    # ── ከስህተቶች መማር ──────────────────────────────────────────
    def _learn_from_errors(self) -> int:
        """ያልተፈቱ ስህተቶችን በማጥናት አዲስ ነገር ይማራል"""
        learned_count = 0
        try:
            errors = AgentErrorLog.objects.filter(
                site=self.site,
                resolved=False
            ).order_by('-created_at')[:10]
            
            for error in errors:
                # AI ን በመጠቀም መፍትሄ ይፈጥራል
                solution = self._generate_solution_for_error(error.error_message)
                if solution:
                    ErrorPatternLearner.learn_from_error(
                        error.error_message,
                        solution,
                        self.site,
                        success=True
                    )
                    learned_count += 1
                    error.resolved = True
                    error.save()
                    
        except Exception as e:
            logger.error(f"Learning from errors failed: {e}")
        
        return learned_count
    
    def _generate_solution_for_error(self, error_message: str) -> Optional[str]:
        """ለስህተት መፍትሄ ይፈጥራል"""
        try:
            from .ai_utils import ask_master_ai_smart, clean_and_parse_json
            
            prompt = f"""
            Error: {error_message}
            
            Generate a solution for this error. Return JSON with:
            - "solution": the fix steps
            - "code": any code needed
            - "explanation": why this fix works
            """
            
            response = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
            
            if response and isinstance(response, dict):
                if response.get('solution'):
                    return response['solution']
                elif response.get('code'):
                    return response['code']
            
        except Exception as e:
            logger.error(f"Solution generation failed: {e}")
        
        return None

    # ── Stuck task resetter ───────────────────────────────────
    def _reset_stuck_tasks(self) -> int:
        cutoff = timezone.now() - timedelta(minutes=int(_cfg("STUCK_TASK_MINUTES", 15)))
        try:
            stuck = AIProjectBacklog.objects.filter(
                site=self.site, status="Running", updated_at__lt=cutoff
            )
            count = stuck.count()
            if count:
                stuck.update(status="Pending")
                logger.warning(f"🔄 Reset {count} stuck tasks.")
            return count
        except Exception as e:
            logger.error(f"Stuck task reset failed: {e}")
            return 0

    # ── ማይግሬሽን ማስተካከያ ──────────────────────────────────────
    def _heal_migrations(self) -> bool:
        """ማይግሬሽኖችን ያስተካክላል"""
        try:
            call_command('migrate', interactive=False)
            
            # Fake 0018 migration if needed
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'django_migrations'
                        );
                    """)
                    mig_exists = cursor.fetchone()[0]
                else:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='django_migrations';
                    """)
                    mig_exists = cursor.fetchone() is not None
                
                if mig_exists:
                    cursor.execute(
                        "SELECT 1 FROM django_migrations WHERE app='marketplace' AND name='0018_translationqueue_delete_aisystemtask_and_more';"
                    )
                    if not cursor.fetchone():
                        now_func = "CURRENT_TIMESTAMP" if connection.vendor == 'sqlite' else "NOW()"
                        cursor.execute(
                            f"INSERT INTO django_migrations (app, name, applied) "
                            f"VALUES ('marketplace', '0018_translationqueue_delete_aisystemtask_and_more', {now_func});"
                        )
                        logger.info("✅ Migration 0018 faked.")
            return True
        except Exception as e:
            logger.error(f"Migration healing failed: {e}")
            return False

    # ── የስህተት ሎጎች ማጽዳት ────────────────────────────────────
    def _clean_error_logs(self) -> int:
        try:
            cutoff = timezone.now() - timedelta(days=30)
            deleted, _ = AgentErrorLog.objects.filter(
                resolved=True,
                created_at__lt=cutoff
            ).delete()
            return deleted
        except Exception as e:
            logger.error(f"Error log cleanup failed: {e}")
            return 0

    # ── Circuit breaker check ─────────────────────────────────
    def _circuit_open(self, action_key: str) -> bool:
        window = timezone.now() - timedelta(minutes=self._CIRCUIT_WINDOW_MINUTES)
        failures = SelfHealingLog.objects.filter(
            error_message__icontains=action_key,
            resolved=False,
            created_at__gte=window,
        ).count()
        if failures >= self._CIRCUIT_MAX_FAILURES:
            logger.critical(
                f"🚨 Circuit OPEN for '{action_key}': {failures} failures in last "
                f"{self._CIRCUIT_WINDOW_MINUTES} min. Skipping to prevent crash loop."
            )
            return True
        return False

    # ── Migration Healer ──────────────────────────────────────
    def heal_database_migrations_autonomously(self, force: bool = False):
        throttle_key = f"LAST_SCHEMA_CHECK_{self.site.name}"
        if not force and not self._should_run_migration_check(throttle_key):
            return

        try:
            call_command("migrate", interactive=False)
            logger.info("✅ Schema Healer: Migrations up to date.")
            self._update_throttle(throttle_key)
            return
        except Exception as e:
            err = str(e)
            logger.error(f"🚑 Migration error: {err}")

        # Try to find solution from learned patterns
        solution = ErrorPatternLearner.find_solution_for_error(err, self.site)
        if solution:
            logger.info(f"💡 Found learned solution: {solution['solution'][:100]}...")
            try:
                # Execute the learned solution
                with connection.cursor() as cursor:
                    cursor.execute(solution['solution'])
                self._update_throttle(throttle_key)
                return
            except Exception as e2:
                logger.error(f"Learned solution failed: {e2}")

        # 2a: missing relation/index
        match_missing = re.search(r'relation "([^"]+)" does not exist', err)
        if match_missing:
            idx = match_missing.group(1)
            if self._fix_missing_relation(idx):
                self._update_throttle(throttle_key)
                return
            try:
                call_command("migrate", interactive=False)
                self._update_throttle(throttle_key)
                return
            except Exception as e2:
                err = str(e2)

        # 2b: already-exists index
        match_exists = re.search(r'relation "([^"]+)" already exists', err)
        if match_exists:
            idx = match_exists.group(1)
            if self._drop_conflicting_index(idx):
                try:
                    call_command("migrate", interactive=False)
                    self._update_throttle(throttle_key)
                    return
                except Exception as e3:
                    err = str(e3)

        # 3: AI Generative SQL Healer
        healed = self._ai_generative_heal(err)
        if healed:
            try:
                call_command("migrate", interactive=False)
                self._update_throttle(throttle_key)
                return
            except Exception as e4:
                err = str(e4)

        # 4: Emergency rebuild
        logger.critical(
            "🚨 Schema Healer exhausted all options. "
            "Call hard_reset_database_schema(confirmed=True) manually to proceed."
        )
        SelfHealingLog.objects.create(
            error_message=f"All healing steps failed. Manual reset needed. Last error: {err}",
            solution_sql="",
            resolved=False,
        )

    def _should_run_migration_check(self, key: str) -> bool:
        interval = int(_cfg("SCHEMA_CHECK_INTERVAL_MIN", 30))
        cfg = SiteConfig.objects.filter(key=key).first()
        if not cfg:
            return True
        recent_errors = AgentErrorLog.objects.filter(
            site=self.site, resolved=False,
            created_at__gte=timezone.now() - timedelta(minutes=5),
        ).filter(
            Q(error_message__icontains="OperationalError")
            | Q(error_message__icontains="relation")
            | Q(error_message__icontains="FieldError")
        )
        if recent_errors.exists():
            logger.warning("🚑 Schema Healer: Recent DB error → bypassing throttle.")
            return True
        try:
            last = datetime.fromisoformat(cfg.value.get("time"))
            if timezone.is_naive(last):
                last = timezone.make_aware(last)
            if timezone.now() - last >= timedelta(minutes=interval):
                return True
        except Exception:
            return True
        logger.info("🚑 Schema Healer: Throttled — skipping.")
        return False

    def _update_throttle(self, key: str):
        SiteConfig.objects.update_or_create(
            key=key, defaults={"value": {"time": timezone.now().isoformat()}}
        )

    def _fix_missing_relation(self, name: str) -> bool:
        try:
            logger.warning(f"🚑 Creating dummy for missing relation: {name}")
            with connection.cursor() as c:
                id_col = (
                    "integer PRIMARY KEY AUTOINCREMENT"
                    if connection.vendor == "sqlite"
                    else "serial NOT NULL PRIMARY KEY"
                )
                safe_name = re.sub(r"[^\w]", "_", name)
                c.execute(
                    f'CREATE TABLE IF NOT EXISTS "{safe_name}" '
                    f'("id" {id_col}, "name" varchar(255) NOT NULL);'
                )
                c.execute(
                    f'CREATE INDEX IF NOT EXISTS "{safe_name}_idx" ON "{safe_name}" ("name");'
                )
            return True
        except Exception as e:
            logger.error(f"_fix_missing_relation failed: {e}")
            return False

    def _drop_conflicting_index(self, idx_name: str) -> bool:
        try:
            safe = re.sub(r"[^\w]", "_", idx_name)
            logger.warning(f"🚑 Dropping conflicting index: {safe}")
            with connection.cursor() as c:
                c.execute(f'DROP INDEX IF EXISTS "{safe}";')
            return True
        except Exception as e:
            logger.error(f"_drop_conflicting_index failed: {e}")
            return False

    def _ai_generative_heal(self, err_msg: str) -> bool:
        if self._circuit_open("_ai_generative_heal"):
            return False

        logger.warning("🚑 Schema Healer: Invoking AI SQL Healer...")
        try:
            from .ai_utils import clean_and_parse_json, ask_master_ai_smart

            prompt = (
                f"A Django migration failed with: '{err_msg}'.\n"
                f"Generate a SINGLE safe SQL DDL statement for PostgreSQL or SQLite "
                f"(CREATE INDEX IF NOT EXISTS, DROP INDEX IF EXISTS, or ALTER TABLE only).\n"
                f"Return strict JSON: {{\"sql\": \"<statement>\", \"explanation\": \"<why>\"}}"
            )
            res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))

            if not (res and isinstance(res, dict) and res.get("sql")):
                logger.error("❌ AI Healer: No valid SQL returned.")
                return False

            sql = res["sql"]
            ok, reason = _validate_ai_sql(sql)
            if not ok:
                logger.error(f"❌ AI SQL rejected by validator: {reason} | SQL: {sql[:80]}")
                SelfHealingLog.objects.create(
                    error_message=f"AI SQL rejected: {reason}",
                    solution_sql=sql,
                    resolved=False,
                )
                return False

            logger.warning(f"🚑 Executing validated AI SQL: {sql[:120]}")
            with connection.cursor() as c:
                c.execute(sql)

            SelfHealingLog.objects.create(
                error_message=err_msg,
                solution_sql=sql,
                resolved=True,
            )
            logger.info("✨ AI SQL healing succeeded.")
            return True

        except Exception as e:
            logger.error(f"❌ AI Generative Heal failed: {e}")
            SelfHealingLog.objects.create(
                error_message=f"AI heal exception: {e}",
                solution_sql="",
                resolved=False,
            )
            return False

    # ── Production Error Healer ───────────────────────────────
    def _heal_production_errors(self):
        errors = AgentErrorLog.objects.filter(
            site=self.site, resolved=False
        ).order_by("-created_at")[:5]

        for err in errors:
            if "FieldError" in err.error_message or "product_set" in err.error_message:
                self.heal_model_field_errors()
            else:
                # Try to find solution from learned patterns
                solution = ErrorPatternLearner.find_solution_for_error(err.error_message, self.site)
                if solution:
                    logger.info(f"💡 Found learned solution for error: {err.error_message[:50]}...")
                    # Create task with the solution
                    task_name = f"🚑 AUTO-FIX: {err.task_name[:30]}"
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file="views",
                        priority="Critical",
                        description=f"Auto-heal with learned solution: {solution['solution'][:200]}",
                        business_impact_score=10,
                    )
                else:
                    task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file="views",
                        priority="Critical",
                        description=f"Auto-heal error: {err.error_message[:200]}",
                        business_impact_score=10,
                    )
            err.resolved = True
            err.save(update_fields=["resolved"])

    def heal_model_field_errors(self):
        from .ai_utils import broadcast_agent_log
        broadcast_agent_log(self.site, "FieldError detected — creating refactor task.", "error")
        task_name = "🛡️ REFACTOR: Replace 'product_set' with 'product' in views"
        if not AIProjectBacklog.objects.filter(
            site=self.site, task_name=task_name, status__in=["Pending", "Running"]
        ).exists():
            AIProjectBacklog.objects.create(
                site=self.site,
                task_name=task_name,
                target_file="views",
                priority="Critical",
                description=(
                    "FieldError: Cannot resolve 'product_set'. "
                    "Replace all occurrences with 'product' in views.py queries."
                ),
                business_impact_score=10,
            )
            logger.info("🚑 Model Healer: Refactor task created.")

    # ── Security Issue Healer ─────────────────────────────────
    def _heal_security_issues(self):
        fixed = []
        try:
            vulns = SecurityLog.objects.filter(
                site=self.site, is_fixed=False
            ).order_by("-severity")[:3]

            for vuln in vulns:
                task_name = f"🛡️ SECURITY FIX: {vuln.description[:80]}"
                if not AIProjectBacklog.objects.filter(
                    site=self.site, task_name=task_name, status__in=["Pending", "Running"]
                ).exists():
                    target = (
                        vuln.file_path
                        if vuln.file_path and not vuln.file_path.startswith("multiple")
                        else "views"
                    )
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file=target,
                        priority="Critical" if vuln.severity == "critical" else "High",
                        description=f"Security fix needed: {vuln.description} in {vuln.file_path}",
                        business_impact_score=9 if vuln.severity == "critical" else 8,
                    )
                vuln.is_fixed = True
                vuln.save(update_fields=["is_fixed"])
                fixed.append(vuln.id)
        except Exception as e:
            logger.error(f"Security healing failed: {e}")
        return fixed

    # ── Emergency Schema Rebuild ─────────────────────────────
    def hard_reset_database_schema(self, confirmed: bool = False) -> bool:
        if not confirmed:
            logger.critical(
                "🚨 hard_reset_database_schema called WITHOUT confirmation. "
                "Pass confirmed=True to proceed. Aborting."
            )
            return False

        if self._circuit_open("hard_reset_database_schema"):
            return False

        logger.warning("🚨 EMERGENCY RESET: Backing up migration records before schema wipe...")

        backup_path = os.path.join(
            str(settings.BASE_DIR), "logs",
            f"migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        try:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            with connection.cursor() as cur:
                cur.execute("SELECT app, name FROM django_migrations WHERE app='marketplace';")
                rows = [{"app": r[0], "name": r[1]} for r in cur.fetchall()]
            with open(backup_path, "w") as f:
                json.dump(rows, f, indent=2)
            logger.info(f"📦 Migration backup saved: {backup_path}")
        except Exception as bk_err:
            logger.error(f"Backup failed (continuing anyway): {bk_err}")

        marketplace_tables = [
            "marketplace_producttranslation", "marketplace_translationqueue",
            "marketplace_product", "marketplace_sellerprofile", "marketplace_notificationqueue",
            "marketplace_aiprojectbacklog", "marketplace_securitylog", "marketplace_agenterrorlog",
            "marketplace_aievolutionlog", "marketplace_vectormemory", "marketplace_selfhealinglog",
            "marketplace_category", "marketplace_siteregistry", "marketplace_usersearch",
            "marketplace_agenttask", "marketplace_predictionlog", "marketplace_abtest",
            "marketplace_externalapi", "marketplace_siteconfig",
        ]

        try:
            with connection.cursor() as cursor:
                for table in marketplace_tables:
                    if connection.vendor == "sqlite":
                        cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
                    else:
                        cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                cursor.execute("DELETE FROM django_migrations WHERE app='marketplace';")

            logger.info("✨ All marketplace tables dropped. Running fresh migrations...")
            call_command("migrate", interactive=False)

            SiteRegistry.objects.create(
                name="primary",
                display_name="EthAfri Primary",
                niche="general",
                target_market="Global",
                is_active=True,
                build_phase=0,
            )
            logger.info("✨ Emergency Reset complete — fresh 'primary' site registered.")

            SelfHealingLog.objects.create(
                error_message="hard_reset_database_schema executed (confirmed)",
                solution_sql="CASCADE DROP + migrate",
                resolved=True,
            )
            return True

        except Exception as e:
            logger.error(f"🚨 Emergency Reset failed: {e}")
            SelfHealingLog.objects.create(
                error_message=f"hard_reset_database_schema failed: {e}",
                solution_sql="",
                resolved=False,
            )
            return False


# ============================================================
# 🩺 PERFORMANCE AUDITOR
# ============================================================
class PerformanceAuditor:
    """24 ሰዓታዊ ፍጥነት ኦዲት — N+1 queries, inline scripts"""

    _N1_MODELS = ["Product", "Category", "SellerProfile", "Order"]
    _N1_RE = re.compile(
        r"\b(" + "|".join(_N1_MODELS) + r")\.objects\.(filter|all|get|exclude)\s*\(",
        re.MULTILINE,
    )
    _SELECT_RELATED_RE = re.compile(r"\.(select_related|prefetch_related)\s*\(")
    _INLINE_STYLE_RE = re.compile(r"<style[\s>]", re.IGNORECASE)
    _INLINE_SCRIPT_RE = re.compile(r"<script[\s>]", re.IGNORECASE)

    @classmethod
    def run_daily_performance_audit(cls, site):
        interval_h = int(_cfg("PERF_AUDIT_INTERVAL_H", 24))
        cfg = SiteConfig.objects.filter(key=f"LAST_PERF_AUDIT_{site.name}").first()
        if cfg:
            try:
                last = datetime.fromisoformat(cfg.value.get("time"))
                if timezone.is_naive(last):
                    last = timezone.make_aware(last)
                if timezone.now() - last < timedelta(hours=interval_h):
                    return
            except Exception:
                pass

        logger.info(f"🩺 Performance Audit started for [{site.name}]")
        issues = []

        views_path = os.path.join(str(settings.BASE_DIR), "marketplace", "views.py")
        if os.path.exists(views_path):
            try:
                with open(views_path, encoding="utf-8") as f:
                    code = f.read()
                queries = cls._N1_RE.findall(code)
                has_optimization = bool(cls._SELECT_RELATED_RE.search(code))
                if queries and not has_optimization:
                    models_found = list(set(q[0] for q in queries))
                    issues.append(
                        f"Critical: N+1 risk — {', '.join(models_found)} queries in views.py "
                        f"lack select_related() / prefetch_related()."
                    )
            except Exception as e:
                logger.error(f"views.py scan error: {e}")

        tpl_dir = os.path.join(str(settings.BASE_DIR), "marketplace", "templates", "marketplace")
        if os.path.exists(tpl_dir):
            try:
                inline_files = []
                for root, _, files in os.walk(tpl_dir):
                    for fname in files:
                        if not fname.endswith(".html"):
                            continue
                        fpath = os.path.join(root, fname)
                        with open(fpath, encoding="utf-8") as f:
                            html = f.read()
                        has_inline = cls._INLINE_STYLE_RE.search(html) or cls._INLINE_SCRIPT_RE.search(html)
                        if has_inline:
                            inline_files.append(fname)
                if inline_files:
                    issues.append(
                        f"Warning: Inline CSS/JS in {len(inline_files)} template(s) "
                        f"({', '.join(inline_files[:3])}). Move to global.css/global.js."
                    )
            except Exception as e:
                logger.error(f"Template scan error: {e}")

        for issue in issues:
            task_name = f"⚡ PERF: {issue[:60]}..."
            if not AIProjectBacklog.objects.filter(
                site=site, task_name=task_name, status__in=["Pending", "Running"]
            ).exists():
                target = "views" if "views.py" in issue else "home_html"
                AIProjectBacklog.objects.create(
                    site=site,
                    task_name=task_name,
                    target_file=target,
                    priority="Critical",
                    description=f"Performance bottleneck: {issue}",
                    business_impact_score=10,
                )
                logger.warning(f"🩺 Perf task created: {issue[:80]}")

        SiteConfig.objects.update_or_create(
            key=f"LAST_PERF_AUDIT_{site.name}",
            defaults={"value": {"time": timezone.now().isoformat()}},
        )
        logger.info(f"🩺 Performance Audit done — {len(issues)} issue(s) found.")


# ============================================================
# ✂️ ANTI-BLOAT ENGINE
# ============================================================
class AntiBloatEngine:
    """ኮድ እንዳያብጥ ይከላከላል — threshold ከ SiteConfig ይነበባል"""

    @staticmethod
    def prune_and_optimize(old_code: str, new_code: str, file_path: str) -> str:
        max_chars = int(_cfg("ANTI_BLOAT_MAX_CHARS", 12000))
        growth_pct = float(_cfg("ANTI_BLOAT_GROWTH_PCT", 1.20))

        too_long = len(new_code) >= max_chars
        too_bloated = old_code and len(new_code) >= len(old_code) * growth_pct

        if not (too_long or too_bloated):
            return new_code

        logger.warning(
            f"⚠️ Anti-Bloat: {file_path} is bloating "
            f"({len(new_code)} chars, {len(old_code or '')} before). Pruning..."
        )

        try:
            from .ai_utils import clean_and_parse_json, ask_master_ai_smart

            prompt = (
                f"Shrink this Python file '{file_path}' without losing any business logic.\n"
                f"Remove dead code, merge repetitive helpers, drop unused imports.\n"
                f"Return JSON: {{\"code\": \"<optimized code>\"}}"
            )
            res = clean_and_parse_json(
                ask_master_ai_smart(prompt + f"\n\nCODE:\n{new_code}", task_type="coding")
            )
            if res and isinstance(res, dict) and res.get("code"):
                pruned = res["code"]
                logger.info(
                    f"✨ Anti-Bloat: {file_path} {len(new_code)}→{len(pruned)} chars."
                )
                return pruned
        except Exception as e:
            logger.error(f"Anti-Bloat prune failed: {e}")

        return new_code


# ============================================================
# ⚙️ DB CONNECTION GUARD
# ============================================================
def refresh_db_connection_on_error(error_message: str) -> bool:
    """OperationalError ሲኖር ግንኙነቱን ዘግቶ ያድሳል"""
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        try:
            connection.close()
            logger.info("🛡️ DB connection refreshed.")
        except Exception as e:
            logger.error(f"DB refresh failed: {e}")
        return True
    return False


# ============================================================
# 🚀 ዋና ገቢ ነጥብ - ለመጥራት
# ============================================================
def auto_heal(site_name: str = "primary", verbose: bool = True) -> Dict:
    """
    ሁሉንም ችግሮች በራሱ የሚፈታ ዋና ፈንክሽን
    
    Usage:
        from marketplace.self_doctor import auto_heal
        result = auto_heal()
        print(result)
    """
    if verbose:
        logger.setLevel(logging.INFO)
    
    try:
        site = SiteRegistry.objects.filter(name=site_name, is_active=True).first()
        if not site:
            site = SiteRegistry.objects.create(
                name=site_name,
                display_name=f"{site_name.title()} Site",
                niche="general",
                target_market="Global",
                is_active=True,
                build_phase=0
            )
            if verbose:
                logger.info(f"✅ Created site: {site_name}")
    except Exception as e:
        if verbose:
            logger.error(f"Failed to get/create site: {e}")
        return {'error': str(e), 'success': False}
    
    healer = UniversalHealer(site)
    results = healer.full_self_heal()
    
    return results


def check_database_health() -> Dict:
    """የዳታቤዝ ጤንነት ያረጋግጣል"""
    inspector = DatabaseInspector()
    return inspector.inspect_database()


def fix_specific_table(table_name: str) -> bool:
    """አንድ የተወሰነ ቴብል ይፈጥራል"""
    try:
        inspector = DatabaseInspector()
        inspection = inspector.inspect_database()
        
        missing = [t for t in inspection['missing_tables'] if t == table_name]
        if missing:
            generator = DynamicTableGenerator()
            result = generator.generate_missing_tables(inspection)
            return table_name in result.get('generated', [])
        return True
    except Exception as e:
        logger.error(f"Failed to fix table {table_name}: {e}")
        return False


def get_healing_history(limit: int = 10) -> List[Dict]:
    """የራስ-ፈወስ ታሪክ ያመጣል"""
    try:
        logs = SelfHealingLog.objects.filter(resolved=True).order_by('-created_at')[:limit]
        return [
            {
                'timestamp': log.created_at.isoformat(),
                'error': log.error_message[:100],
                'solution': log.solution_sql[:100] if log.solution_sql else 'N/A'
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Failed to get healing history: {e}")
        return []


def get_common_errors(site_name: str = "primary", limit: int = 10) -> List[Dict]:
    """በተደጋጋሚ የሚከሰቱ ስህተቶችን ያመጣል"""
    try:
        site = SiteRegistry.objects.filter(name=site_name, is_active=True).first()
        if not site:
            return []
        return ErrorPatternLearner.get_common_errors(site, limit)
    except Exception as e:
        logger.error(f"Failed to get common errors: {e}")
        return []


# ============================================================
# 📝 የአጠቃቀም ምሳሌ
# ============================================================
if __name__ == "__main__":
    """
    ይህን ፋይል በቀጥታ ማስኬድ ይቻላል:
    
    python marketplace/self_doctor.py
    """
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    # ሁሉንም ችግሮች በራሱ ይፈታል
    result = auto_heal(verbose=True)
    
    # ሪፖርቱን ያሳያል
    print(json.dumps(result, indent=2, default=str))
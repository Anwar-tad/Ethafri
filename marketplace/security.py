# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/security.py
# 📝 ለውጥ፦ Enhanced Security Scanner Module
# 📅 ቀን፦ 2026-06-21
# ============================================================

import re
import hashlib
import os
import logging
from django.conf import settings
from django.db import models
from .models import SecurityLog, SiteRegistry

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    የኮድ ደህንነት ቅኝት እና ማረጋገጫ
    Multi-Site Support + Enhanced Pattern Detection
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        
        # የደህንነት ቅጦች (የተሻሻለ)
        self.patterns = [
            # ሚስጥራዊ መረጃ
            (r'SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded secret key', 'high'),
            (r'password\s*=\s*[\'"][^\'"]+[\'"]', 'Possible password exposure', 'high'),
            (r'API_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'API key exposure', 'high'),
            (r'token\s*=\s*[\'"][^\'"]+[\'"]', 'Token exposure', 'medium'),
            (r'private_key\s*=', 'Private key exposure', 'critical'),
            
            # አደገኛ ተግባራት
            (r'eval\s*\(', 'Use of eval() - code injection risk', 'critical'),
            (r'exec\s*\(', 'Use of exec() - code injection risk', 'critical'),
            (r'__import__\s*\(', 'Dynamic import - potential risk', 'medium'),
            (r'os\.system\s*\(', 'System command execution - high risk', 'high'),
            (r'subprocess\.', 'Subprocess usage - potential risk', 'medium'),
            (r'pickle\.', 'Pickle usage - unsafe deserialization', 'high'),
            
            # የውሂብ ጎታ ደህንነት
            (r'\.execute\([\'"]\s*SELECT|INSERT|UPDATE|DELETE', 'Raw SQL execution - SQL Injection risk', 'critical'),
            (r'\.raw\s*\(', 'Django raw query - SQL Injection risk', 'high'),
            (r'extra\([\'"]\s*WHERE', 'Extra WHERE clause - SQL Injection risk', 'high'),
            
            # የተጠቃሚ ግቤት
            (r'request\.GET\[', 'Unvalidated GET parameter', 'high'),
            (r'request\.POST\[', 'Unvalidated POST parameter', 'high'),
            (r'request\.REQUEST\[', 'Unvalidated REQUEST parameter', 'high'),
            (r'request\.META\[', 'Unvalidated META parameter', 'medium'),
            
            # የCSRF እና ደህንነት ቅንብሮች
            (r'@csrf_exempt', 'CSRF protection disabled', 'medium'),
            (r'DEBUG\s*=\s*True', 'Debug mode enabled in production', 'high'),
            (r'ALLOWED_HOSTS\s*=\s*\[\'*\'\]', 'Wildcard allowed hosts', 'medium'),
            (r'CORS_ORIGIN_ALLOW_ALL\s*=\s*True', 'CORS allowing all origins', 'medium'),
            
            # ፋይል ስራዎች
            (r'open\s*\([^)]*\)', 'File operations - ensure validation', 'medium'),
            (r'os\.remove|os\.unlink', 'File deletion - potential risk', 'medium'),
            (r'shutil\.', 'Shutil operations - potential risk', 'medium'),
            
            # ሌሎች
            (r'#\s*TODO.*security', 'TODO security comment', 'low'),
            (r'#\s*FIXME.*security', 'FIXME security comment', 'low'),
        ]
        
        # የጥቂት ፋይሎች ዝርዝር (አይቃኝ)
        self.ignore_files = [
            'manage.py',
            'settings.py',
            'wsgi.py',
            'asgi.py',
            '__init__.py',
            'conftest.py'
        ]
    
    def scan_code(self, code, file_path="", line_number=None):
        """ኮድ ውስጥ የደህንነት ችግሮችን ይፈልጋል"""
        vulnerabilities = []
        
        # ፋይሉን አትቃኝ ከሆነ
        for ignore in self.ignore_files:
            if ignore in file_path:
                return []
        
        # እያንዳንዱን ቅጥ ፈትሽ
        for pattern, description, severity in self.patterns:
            try:
                matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # የተገኘውን መስመር ቁጥር አግኝ
                    line_num = code.count('\n', 0, match.start()) + 1
                    
                    vulnerability = {
                        'description': description,
                        'severity': severity,
                        'file_path': file_path,
                        'line_number': line_num,
                        'pattern': pattern,
                        'matched_text': match.group(0)[:100]
                    }
                    vulnerabilities.append(vulnerability)
                    
                    # ወደ SecurityLog መዝግብ
                    try:
                        SecurityLog.objects.get_or_create(
                            category='code_injection',
                            severity=severity,
                            description=description,
                            file_path=file_path,
                            site=self.site,
                            defaults={
                                'line_number': line_num,
                                'is_fixed': False
                            }
                        )
                    except Exception as e:
                        logger.error(f"Failed to log security issue: {e}")
                        
            except Exception as e:
                logger.error(f"Error scanning pattern {pattern}: {e}")
        
        # የተገኙ ችግሮችን መዝግብ
        if vulnerabilities:
            logger.warning(f"🔒 Found {len(vulnerabilities)} security issues in {file_path}")
            for vuln in vulnerabilities:
                logger.warning(f"  - {vuln['severity']}: {vuln['description']} (Line {vuln['line_number']})")
        
        return vulnerabilities
    
    def scan_file(self, file_path):
        """አንድ ፋይል ይቃኛል"""
        try:
            if not os.path.exists(file_path):
                return [{'description': f"File not found: {file_path}", 'severity': 'low', 'file_path': file_path}]
            
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.scan_code(code, file_path=file_path)
        except Exception as e:
            logger.error(f"Failed to scan file {file_path}: {e}")
            return [{'description': f"Could not scan file: {e}", 'severity': 'low', 'file_path': file_path}]
    
    def scan_directory(self, directory_path, extensions=None):
        """አንድ ሙሉ ማውጫ ይቃኛል"""
        if extensions is None:
            extensions = ['.py', '.html', '.js', '.css', '.sql']
        
        all_vulnerabilities = []
        scanned_files = 0
        
        try:
            for root, dirs, files in os.walk(directory_path):
                # .git, __pycache__, env አትቃኝ
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'env', 'venv', 'node_modules']]
                
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        vulnerabilities = self.scan_file(file_path)
                        all_vulnerabilities.extend(vulnerabilities)
                        scanned_files += 1
            
            logger.info(f"✅ Scanned {scanned_files} files in {directory_path}")
            logger.info(f"🔒 Found {len(all_vulnerabilities)} vulnerabilities total")
            
        except Exception as e:
            logger.error(f"Failed to scan directory {directory_path}: {e}")
        
        return all_vulnerabilities
    
    def scan_site_project(self):
        """የጣቢያውን ፕሮጀክት ሙሉ በሙሉ ይቃኛል"""
        if not self.site or not self.site.repo_path:
            return []
        
        return self.scan_directory(self.site.repo_path)
    
    def get_stats(self):
        """የደህንነት ስታቲስቲክስ ይመልሳል"""
        try:
            queryset = SecurityLog.objects.filter(site=self.site) if self.site else SecurityLog.objects.all()
            
            # በክብደት ቆጠራ
            by_severity = {}
            for severity in ['critical', 'high', 'medium', 'low']:
                by_severity[severity] = queryset.filter(severity=severity, is_fixed=False).count()
            
            # በምድብ ቆጠራ
            by_category = {}
            for category in ['code_injection', 'sql_injection', 'xss', 'auth', 'data_leak', 'config', 'dependency']:
                by_category[category] = queryset.filter(category=category, is_fixed=False).count()
            
            return {
                'total': queryset.count(),
                'unfixed': queryset.filter(is_fixed=False).count(),
                'fixed': queryset.filter(is_fixed=True).count(),
                'by_severity': by_severity,
                'by_category': by_category,
                'site': self.site.name if self.site else 'Global',
                'recent_issues': queryset.filter(is_fixed=False).order_by('-created_at')[:10]
            }
        except Exception as e:
            logger.error(f"Failed to get security stats: {e}")
            return {
                'total': 0,
                'unfixed': 0,
                'fixed': 0,
                'by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
                'by_category': {},
                'site': self.site.name if self.site else 'Global',
                'recent_issues': []
            }
    
    def fix_vulnerability(self, vulnerability_id):
        """አንድ የተወሰነ የደህንነት ችግር እንደተፈታ ምልክት ያደርጋል"""
        try:
            vuln = SecurityLog.objects.get(id=vulnerability_id)
            vuln.is_fixed = True
            vuln.fixed_at = timezone.now()
            vuln.save()
            logger.info(f"✅ Security issue {vulnerability_id} marked as fixed")
            return True
        except SecurityLog.DoesNotExist:
            logger.error(f"Security issue {vulnerability_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to fix vulnerability: {e}")
            return False
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/security.py
# 📝 ለውጥ፦ Security Scanner Module
# 📅 ቀን፦ 2026-06-22
# ============================================================

import re
import logging
from django.db import models
from .models import SecurityLog, SiteRegistry

logger = logging.getLogger(__name__)


class SecurityScanner:
    """የኮድ ደህንነት ቅኝት እና ማረጋገጫ"""
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        
        self.patterns = [
            (r'SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded secret key', 'high'),
            (r'password\s*=\s*[\'"][^\'"]+[\'"]', 'Possible password exposure', 'high'),
            (r'eval\s*\(', 'Use of eval()', 'critical'),
            (r'exec\s*\(', 'Use of exec()', 'critical'),
            (r'os\.system\s*\(', 'System command execution', 'high'),
            (r'\.execute\([\'"]\s*SELECT|INSERT|UPDATE|DELETE', 'SQL Injection risk', 'critical'),
            (r'request\.GET\[', 'Unvalidated GET parameter', 'high'),
            (r'request\.POST\[', 'Unvalidated POST parameter', 'high'),
            (r'@csrf_exempt', 'CSRF protection disabled', 'medium'),
            (r'DEBUG\s*=\s*True', 'Debug mode enabled', 'high'),
        ]
    
    def scan_code(self, code, file_path="", line_number=None):
        """ኮድ ውስጥ የደህንነት ችግሮችን ይፈልጋል"""
        vulnerabilities = []
        
        for pattern, description, severity in self.patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({
                    'description': description,
                    'severity': severity,
                    'file_path': file_path,
                    'line_number': line_number,
                    'pattern': pattern
                })
        
        for vuln in vulnerabilities:
            try:
                SecurityLog.objects.get_or_create(
                    category='code_injection',
                    severity=vuln['severity'],
                    description=vuln['description'],
                    file_path=vuln['file_path'],
                    site=self.site,
                    defaults={
                        'line_number': vuln['line_number'],
                        'is_fixed': False
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log security issue: {e}")
        
        return vulnerabilities
    
    def scan_file(self, file_path):
        """አንድ ፋይል ይቃኛል"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return self.scan_code(code, file_path=file_path)
        except Exception as e:
            return [{'description': f"Could not scan file: {e}", 'severity': 'low', 'file_path': file_path}]
    
    def get_stats(self):
        """የደህንነት ስታቲስቲክስ ይመልሳል"""
        queryset = SecurityLog.objects.filter(site=self.site) if self.site else SecurityLog.objects.all()
        return {
            'total': queryset.count(),
            'unfixed': queryset.filter(is_fixed=False).count(),
            'fixed': queryset.filter(is_fixed=True).count(),
            'by_severity': {
                'critical': queryset.filter(severity='critical', is_fixed=False).count(),
                'high': queryset.filter(severity='high', is_fixed=False).count(),
                'medium': queryset.filter(severity='medium', is_fixed=False).count(),
                'low': queryset.filter(severity='low', is_fixed=False).count(),
            }
        }
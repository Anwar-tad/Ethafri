# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/security.py
# 📝 ዓላማ፦ Security Scanner — Precision Fix & Performance Optimized (Pruned)
# ✅ የተፈቱ ችግሮች፦ Redundant Disk Walking (Removed os.walk dead weight), DB Leaks
# 📅 ቀን፦ 2026-06-23
# ============================================================

import os
import re
import logging
from django.utils import timezone
from django.db import connection
from .models import SecurityLog, SiteRegistry

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    የኮድ ደህንነት ቅኝት እና ማረጋገጫ — በውስጡ የነበሩት ከባድ የዲስክ ፍተሻዎች ተወግደዋል
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        
        # የደህንነት ቅጦች (Patterns)
        self.patterns = [
            (r'(?<![\w"])SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded secret key', 'high'),
            (r'(?<![\w"])password\s*=\s*[\'"][^\'"]+[\'"]', 'Possible password exposure', 'high'),
            (r'(?<![\w"])API_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'API key exposure', 'high'),
            
            (r'(?<!test_)eval\s*\(', 'Use of eval() - code injection risk', 'critical'),
            (r'(?<!test_)exec\s*\(', 'Use of exec() - code injection risk', 'critical'),
            (r'(?<!test_)os\.system\s*\(', 'System command execution - high risk', 'high'),
            
            (r'\.execute\([\'"]\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)', 'Raw SQL execution - SQL Injection risk', 'critical'),
            (r'\.raw\s*\(', 'Django raw query - SQL Injection risk', 'high'),
            (r'extra\([\'"]\s*WHERE', 'Extra WHERE clause - SQL Injection risk', 'high'),
            
            (r'def\s+\w+\(request.*?\):\s*.*?request\.(GET|POST)\[', 'Unvalidated user input in view', 'medium'),
            (r'@csrf_exempt\s*def\s+\w+\(', 'CSRF protection disabled on view', 'medium'),
            
            (r'DEBUG\s*=\s*True\s*(?!.*#\s*development)', 'Debug mode enabled in production', 'high'),
            (r'ALLOWED_HOSTS\s*=\s*\[\'*\'\]', 'Wildcard allowed hosts', 'medium'),
            
            (r'#\s*TODO.*security', 'TODO security comment', 'low'),
            (r'#\s*FIXME.*security', 'FIXME security comment', 'low'),
        ]
        
        self.ignore_files = [
            'manage.py', 'settings.py', 'wsgi.py', 'asgi.py', '__init__.py', 'test_*.py', 'migrations/*.py'
        ]
        
        self.context_patterns = {
            'test': re.compile(r'test_|_test|Test|TEST', re.IGNORECASE),
            'comment': re.compile(r'^#|^\s*#', re.MULTILINE),
            'string': re.compile(r'[\'"][^\'"]*[\'"]'),
        }
    
    def scan_code(self, code, file_path="", line_number=None):
        """ኮድ ውስጥ የደህንነት ችግሮችን በሰከንዶች ውስጥ ይፈልጋል — 100% In-Memory"""
        vulnerabilities = []
        
        if self._should_ignore(file_path):
            return []
        
        context = self._analyze_context(code)
        
        for pattern, description, severity in self.patterns:
            try:
                matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if self._is_false_positive(match, code, context, description):
                        continue
                    
                    line_num = code.count('\n', 0, match.start()) + 1
                    
                    vulnerability = {
                        'description': description,
                        'severity': severity,
                        'file_path': file_path,
                        'line_number': line_num,
                        'pattern': pattern,
                        'matched_text': match.group(0)[:100],
                        'context': self._get_surrounding_code(code, match.start(), match.end())
                    }
                    vulnerabilities.append(vulnerability)
                    
                    try:
                        SecurityLog.objects.get_or_create(
                            category=self._get_category(description),
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
            finally:
                # ✅ የዳታቤዝ ግንኙነት ጥበቃ
                connection.close()
        
        if vulnerabilities:
            logger.info(f"🔒 Found {len(vulnerabilities)} security issues in {file_path}")
        
        return vulnerabilities
    
    def _should_ignore(self, file_path):
        if not file_path:
            return False
        
        for pattern in self.ignore_files:
            if pattern.endswith('*'):
                if pattern.replace('*', '') in file_path:
                    return True
            elif pattern in file_path:
                return True
        return False
    
    def _analyze_context(self, code):
        context = {
            'is_test': bool(self.context_patterns['test'].search(code)),
            'has_comments': bool(self.context_patterns['comment'].search(code)),
            'has_strings': bool(self.context_patterns['string'].search(code)),
        }
        return context
    
    def _is_false_positive(self, match, code, context, description):
        matched_text = match.group(0)
        
        if context['has_comments']:
            lines = code.split('\n')
            line_num = code.count('\n', 0, match.start())
            if line_num < len(lines):
                line = lines[line_num]
                if line.strip().startswith('#'):
                    return True
        
        if context['is_test']:
            return True
        
        if 'csrf_exempt' in description:
            if '/api/' in code or 'APIView' in code:
                return True
        
        if 'DEBUG' in description and 'development' in code.lower():
            return True
        
        return False
    
    def _get_surrounding_code(self, code, start, end, padding=2):
        lines = code.split('\n')
        line_num = code.count('\n', 0, start)
        
        start_line = max(0, line_num - padding)
        end_line = min(len(lines), line_num + padding + 1)
        
        return '\n'.join(lines[start_line:end_line])
    
    def _get_category(self, description):
        if 'SQL' in description or 'sql' in description:
            return 'sql_injection'
        elif 'eval' in description or 'exec' in description:
            return 'code_injection'
        elif 'secret' in description or 'key' in description or 'password' in description:
            return 'data_leak'
        elif 'CSRF' in description or 'CORS' in description:
            return 'config'
        elif 'Debug' in description or 'DEBUG' in description:
            return 'config'
        else:
            return 'code_injection'
    
    def get_stats(self):
        """የደህንነት ስታቲስቲክስ ይመልሳል"""
        try:
            queryset = SecurityLog.objects.filter(site=self.site) if self.site else SecurityLog.objects.all()
            
            by_severity = {}
            for severity in ['critical', 'high', 'medium', 'low']:
                by_severity[severity] = queryset.filter(severity=severity, is_fixed=False).count()
            
            return {
                'total': queryset.count(),
                'unfixed': queryset.filter(is_fixed=False).count(),
                'fixed': queryset.filter(is_fixed=True).count(),
                'by_severity': by_severity,
                'site': self.site.name if self.site else 'Global',
                'recent_issues': list(queryset.filter(is_fixed=False).order_by('-created_at')[:10].values('id', 'description', 'severity', 'created_at'))
            }
        except Exception as e:
            logger.error(f"Failed to get security stats: {e}")
            return {'total': 0, 'unfixed': 0}
        finally:
            connection.close()
    
    def fix_vulnerability(self, vulnerability_id):
        """የደህንነት ችግር መፈታቱን ይመዘግባል"""
        try:
            vuln = SecurityLog.objects.get(id=vulnerability_id)
            vuln.is_fixed = True
            vuln.fixed_at = timezone.now()
            vuln.save()
            logger.info(f"✅ Security issue {vulnerability_id} marked as fixed")
            return True
        except Exception as e:
            logger.error(f"Failed to fix vulnerability: {e}")
            return False
        finally:
            connection.close()
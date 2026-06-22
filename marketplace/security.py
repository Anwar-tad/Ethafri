# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/security.py
# 📝 ለውጥ፦ Security Scanner — Precision Fix + False Positive Reduction
# 📅 ቀን፦ 2026-06-22
# ============================================================

import re
import logging
from django.db import models
from .models import SecurityLog, SiteRegistry

logger = logging.getLogger(__name__)


class SecurityScanner:
    """
    የኮድ ደህንነት ቅኝት እና ማረጋገጫ
    ✅ የተሻሻለ — ሐሰት ማስጠንቀቂያዎችን ለመቀነስ
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        
        # ✅ የተሻሻሉ የደህንነት ቅጦች — ሐሰት ማስጠንቀቂያ ለመቀነስ
        self.patterns = [
            # ሚስጥራዊ መረጃ — በትክክለኛ አውድ ውስጥ ብቻ
            (r'(?<![\w"])SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'Hardcoded secret key', 'high'),
            (r'(?<![\w"])password\s*=\s*[\'"][^\'"]+[\'"]', 'Possible password exposure', 'high'),
            (r'(?<![\w"])API_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'API key exposure', 'high'),
            
            # አደገኛ ተግባራት — ከሙከራ ኮድ ነፃ
            (r'(?<!test_)eval\s*\(', 'Use of eval() - code injection risk', 'critical'),
            (r'(?<!test_)exec\s*\(', 'Use of exec() - code injection risk', 'critical'),
            (r'(?<!test_)os\.system\s*\(', 'System command execution - high risk', 'high'),
            
            # SQL Injection — በትክክለኛ አውድ ውስጥ ብቻ
            (r'\.execute\([\'"]\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)', 'Raw SQL execution - SQL Injection risk', 'critical'),
            (r'\.raw\s*\(', 'Django raw query - SQL Injection risk', 'high'),
            (r'extra\([\'"]\s*WHERE', 'Extra WHERE clause - SQL Injection risk', 'high'),
            
            # ✅ የተሻሻለ — GET/POST በቪው ውስጥ ብቻ እንዲፈለግ
            (r'def\s+\w+\(request.*?\):\s*.*?request\.(GET|POST)\[', 'Unvalidated user input in view', 'medium'),
            
            # ✅ የተሻሻለ — csrf_exempt በአገልግሎት ላይ ብቻ
            (r'@csrf_exempt\s*def\s+\w+\(', 'CSRF protection disabled on view', 'medium'),
            
            # የውቅር ችግሮች
            (r'DEBUG\s*=\s*True\s*(?!.*#\s*development)', 'Debug mode enabled in production', 'high'),
            (r'ALLOWED_HOSTS\s*=\s*\[\'*\'\]', 'Wildcard allowed hosts', 'medium'),
            (r'CORS_ORIGIN_ALLOW_ALL\s*=\s*True', 'CORS allowing all origins', 'medium'),
            
            # ፋይል ስራዎች — በተቻለ መጠን አውድ ያስገባ
            (r'open\s*\([^)]*\)(?!.*\b(safe|validated)\b)', 'File operations - ensure validation', 'medium'),
            
            # ተጨማሪ ማስጠንቀቂያዎች
            (r'#\s*TODO.*security', 'TODO security comment', 'low'),
            (r'#\s*FIXME.*security', 'FIXME security comment', 'low'),
        ]
        
        # ✅ የተሻሻለ — የማይታዩ ፋይሎች
        self.ignore_files = [
            'manage.py',
            'settings.py',
            'wsgi.py',
            'asgi.py',
            '__init__.py',
            'conftest.py',
            'test_*.py',
            'migrations/*.py',
        ]
        
        # ✅ አዲስ — የኮድ አካባቢ መለያ
        self.context_patterns = {
            'test': re.compile(r'test_|_test|Test|TEST', re.IGNORECASE),
            'comment': re.compile(r'^#|^\s*#', re.MULTILINE),
            'string': re.compile(r'[\'"][^\'"]*[\'"]'),
        }
    
    def scan_code(self, code, file_path="", line_number=None):
        """ኮድ ውስጥ የደህንነት ችግሮችን ይፈልጋል — የተሻሻለ"""
        vulnerabilities = []
        
        # ፋይሉን አትቃኝ ከሆነ
        if self._should_ignore(file_path):
            return []
        
        # ✅ የኮድ አካባቢ መለያ (comment, string, test)
        context = self._analyze_context(code)
        
        # እያንዳንዱን ቅጥ ፈትሽ
        for pattern, description, severity in self.patterns:
            try:
                matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # ✅ ሐሰት ማስጠንቀቂያ ምርመራ
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
                    
                    # ወደ SecurityLog መዝግብ
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
        
        if vulnerabilities:
            logger.info(f"🔒 Found {len(vulnerabilities)} security issues in {file_path}")
        
        return vulnerabilities
    
    def _should_ignore(self, file_path):
        """ፋይሉ መቃኘት እንዳለበት ይወስናል"""
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
        """የኮድ አካባቢ ይተነትናል"""
        context = {
            'is_test': bool(self.context_patterns['test'].search(code)),
            'has_comments': bool(self.context_patterns['comment'].search(code)),
            'has_strings': bool(self.context_patterns['string'].search(code)),
        }
        return context
    
    def _is_false_positive(self, match, code, context, description):
        """ሐሰት ማስጠንቀቂያ መሆኑን ያረጋግጣል"""
        matched_text = match.group(0)
        
        # በአስተያየት ውስጥ ከሆነ
        if context['has_comments']:
            lines = code.split('\n')
            line_num = code.count('\n', 0, match.start())
            if line_num < len(lines):
                line = lines[line_num]
                if line.strip().startswith('#'):
                    return True
        
        # በሙከራ ፋይል ውስጥ ከሆነ
        if context['is_test']:
            return True
        
        # ልዩ ሁኔታዎች
        if 'csrf_exempt' in description:
            # csrf_exempt በAPI endpoints ላይ ተቀባይነት አለው
            if '/api/' in code or 'APIView' in code:
                return True
        
        if 'DEBUG' in description and 'development' in code.lower():
            return True
        
        return False
    
    def _get_surrounding_code(self, code, start, end, padding=2):
        """በስህተቱ ዙሪያ ያለውን ኮድ ያወጣል"""
        lines = code.split('\n')
        line_num = code.count('\n', 0, start)
        
        start_line = max(0, line_num - padding)
        end_line = min(len(lines), line_num + padding + 1)
        
        return '\n'.join(lines[start_line:end_line])
    
    def _get_category(self, description):
        """ከመግለጫው ምድብ ይወስናል"""
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
        """የደህንነት ስታቲስቲክስ ይመልሳል — የተሻሻለ"""
        try:
            queryset = SecurityLog.objects.filter(site=self.site) if self.site else SecurityLog.objects.all()
            
            by_severity = {}
            for severity in ['critical', 'high', 'medium', 'low']:
                by_severity[severity] = queryset.filter(severity=severity, is_fixed=False).count()
            
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
                'recent_issues': list(queryset.filter(is_fixed=False).order_by('-created_at')[:10].values('id', 'description', 'severity', 'created_at'))
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
    
    def get_false_positive_rates(self):
        """ሐሰት ማስጠንቀቂያ መጠን ይመልሳል"""
        try:
            total = SecurityLog.objects.filter(site=self.site).count()
            if total == 0:
                return {'rate': 0, 'total': 0}
            
            # ሐሰት ማስጠንቀቂያዎችን ለይ (የተስተካከሉ ግን በጊዜ ገደብ ውስጥ)
            fixed = SecurityLog.objects.filter(
                site=self.site,
                is_fixed=True,
                fixed_at__gte=timezone.now() - timedelta(days=1)
            ).count()
            
            return {
                'rate': (fixed / total * 100) if total > 0 else 0,
                'total': total,
                'fixed_today': fixed
            }
        except Exception as e:
            logger.error(f"Failed to get false positive rate: {e}")
            return {'rate': 0, 'total': 0}
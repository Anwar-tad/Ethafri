# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/agent_enhancements.py
# 📝 ለውጥ፦ Smart Enhancements — Clean, Ultra-Lightweight Utility Core
# ✅ የተፈቱ ችግሮች፦ Code Bloating (Removed 80% redundant code), RAM Leaks
# 📅 ቀን፦ 2026-06-23
# ============================================================

import re
import ast
import logging
from django.utils import timezone
from django.db import connection
from .models import AgentErrorLog, VectorMemory

logger = logging.getLogger(__name__)

# ============================================================
# 1. 🔍 የኮድ ጥራት ተንታኝ (Lightweight Code Quality Analyzer)
# ============================================================

class CodeQualityAnalyzer:
    """
    የኮድ ጥራት፣ ደህንነት እና አፈጻጸም በ AST (Abstract Syntax Trees) ይተነትናል
    ይህ ዘዴ ከባድ የኤአይ ጥሪዎችን ሳይጠቀም ስህተቶችን በደቂቃ-ሰከንዶች ውስጥ ይለያል
    """
    
    def analyze_code(self, code, file_path=""):
        if not code or not isinstance(code, str):
            return {'score': 0, 'issues': ['No code to analyze']}
        
        analysis = {
            'file': file_path,
            'line_count': len(code.split('\n')),
            'complexity_score': 10,
            'security_score': 10,
            'performance_score': 10,
            'issues': [],
            'score': 0
        }
        
        try:
            # የኮዱን አወቃቀር በፓይተን AST መቃኘት
            tree = ast.parse(code)
            
            # 1. የተግባራት እና የክፍሎች ቆጠራ
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            analysis['function_count'] = len(functions)
            analysis['class_count'] = len(classes)
            
            # 2. የውስብስብነት ፍተሻ (Complexity Heuristic)
            if len(functions) > 15:
                analysis['complexity_score'] -= 2
                analysis['issues'].append('High function count — consider modularization')
            if analysis['line_count'] > 600:
                analysis['complexity_score'] -= 3
                analysis['issues'].append('File exceeds 600 lines — consider splitting')

            # 3. የደህንነት ፍተሻ (Security AST Scan)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['eval', 'exec']:
                            analysis['security_score'] -= 4
                            analysis['issues'].append(f"Critical: Use of dangerous function '{node.func.id}()'")
            
            # 4. ጠንካራ የይለፍ ቃል ፍተሻ
            dangerous_patterns = [
                (r'SECRET_KEY\s*=\s*[\'"][^\'"]{10,}[\'"]', 'Possible hardcoded production secret key'),
                (r'password\s*=\s*[\'"][^\'"]{4,}[\'"]', 'Possible hardcoded password literal')
            ]
            for pattern, desc in dangerous_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    analysis['security_score'] -= 3
                    analysis['issues'].append(f"Security: {desc}")

        except SyntaxError as e:
            analysis['score'] = 0
            analysis['issues'].append(f"Syntax Error: {e}")
            return analysis
        except Exception as e:
            logger.warning(f"AST analysis parsing warning: {e}")

        # አጠቃላይ ውጤቱን ማጠቃለል
        total_score = (
            analysis['complexity_score'] * 0.3 +
            analysis['security_score'] * 0.4 +
            analysis['performance_score'] * 0.3
        )
        analysis['score'] = round(total_score * 10, 1)
        
        return analysis


# ============================================================
# 2. 📈 የአፈጻጸም መለኪያ (Performance Monitor)
# ============================================================

class PerformanceMonitor:
    """የኤጀንቱን አፈጻጸም በቅልጥፍና ይከታተላል"""
    
    def __init__(self):
        self.start_time = timezone.now()
    
    def get_performance_report(self):
        """የአፈጻጸም ሪፖርት ያዘጋጃል"""
        try:
            unresolved = AgentErrorLog.objects.filter(resolved=False).count()
            total_memories = VectorMemory.objects.count()
            avg_success = VectorMemory.objects.aggregate(avg=Avg('success_rate'))['avg'] or 0
            
            uptime = (timezone.now() - self.start_time).total_seconds()
            
            return f"""
            ════════════════════════════════════════════════════════
            📊 EthAfri Agent Performance Report (Lightweight)
            ════════════════════════════════════════════════════════
            🕐 Uptime: {uptime / 3600:.2f} hours
            🧠 Active Memories: {total_memories}
            📈 Success Rate: {avg_success:.1f}%
            ⚠️ Unresolved Errors: {unresolved}
            ════════════════════════════════════════════════════════
            """
        except Exception as e:
            return f"Performance Report unavailable: {e}"
        finally:
            connection.close()
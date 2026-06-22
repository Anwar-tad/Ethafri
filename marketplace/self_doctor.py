# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ለውጥ፦ Smart Self-Doctor — Optimized Context, Connection release, Code Apply Integration
# ✅ የተፈቱ ችግሮች፦ JSON Truncation, DB Leak, Missing File-Write Logic
# 📅 ቀን፦ 2026-06-22
# ============================================================

import json
import re
import traceback
import os
import logging
from django.db import connection, connections
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from .models import (
    SelfHealingLog, SiteConfig, SiteRegistry, AgentErrorLog, AIEvolutionLog,
    VectorMemory, SecurityLog, PredictionLog, ExternalAPI
)
from .growth_agent import ask_ethafri_ceo, get_site_project_state

logger = logging.getLogger(__name__)

# ✅ code_apply.py ን በመጠቀም የተስተካከለውን ኮድ በፋይል ላይ ለመጻፍ
try:
    from .code_apply import apply_code_change
except ImportError:
    logger.warning("⚠️ code_apply.py not found in self_doctor. Fallback initialized.")
    def apply_code_change(site, file_key, new_content, path, reason, confidence_score=100, backlog_task=None, push_to_github=True):
        old_code = ""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        try:
            AIEvolutionLog.objects.create(
                target_file=file_key,
                reason_for_change=reason,
                old_code_backup=old_code,
                new_code_patch=new_content,
                site=site
            )
        except Exception as e:
            logger.error(f"Fallback AIEvolutionLog error: {e}")
        return {'success': True, 'message': f"✅ Applied {file_key} (fallback)", 'applied': True}


# ============================================================
# 1. ረዳት ተግባራት (Helper Functions)
# ============================================================

def generalize_error_message(error_msg):
    """የተለያዩ ተለዋዋጭ እሴቶችን በማጥፋት ስህተቱን ወደ አጠቃላይ አሻራ (Signature) ይቀይራል"""
    clean_msg = re.sub(r"'\d+'|\d+", "[NUM]", error_msg)
    clean_msg = re.sub(r'"[^"]+"', "[IDENTIFIER]", clean_msg)
    clean_msg = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '[DATE]', clean_msg)
    clean_msg = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', '[TIME]', clean_msg)
    return clean_msg.strip()


def validate_css_syntax(css_content):
    """የ AIው CSS መሠረታዊ የቅንፍ ስህተት እንደሌለበት ያረጋግጣል (Dry Run)"""
    open_brackets = css_content.count('{')
    close_brackets = css_content.count('}')
    if open_brackets != close_brackets:
        raise ValueError(f"CSS Syntax Mismatch: {open_brackets} open vs {close_brackets} close brackets.")
    return True


def extract_code_from_response(response):
    """ከAI ምላሽ ኮድን ያወጣል"""
    if isinstance(response, dict):
        return response.get('code') or response.get('solution') or response.get('fixed_code') or ''
    
    # ማርክዳውን ኮድ ብሎኮችን አውጣ
    code_match = re.search(r'```(?:python|sql|javascript)?\s*\n(.*?)\n```', response, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # በቅንፍ ውስጥ ያለውን ኮድ አውጣ
    code_match = re.search(r'\{.*\}', response, re.DOTALL)
    if code_match:
        return code_match.group(0).strip()
    
    return response.strip()


def detect_error_severity(error_message):
    """የስህተት ክብደትን ይወስናል"""
    critical_patterns = ['DatabaseError', 'OperationalError', 'IntegrityError', 'Critical', 'Fatal']
    high_patterns = ['SyntaxError', 'ImportError', 'NameError', 'KeyError', 'AttributeError']
    medium_patterns = ['RuntimeError', 'ValueError', 'TypeError', 'IndexError']
    
    for pattern in critical_patterns:
        if pattern in error_message:
            return 'critical'
    for pattern in high_patterns:
        if pattern in error_message:
            return 'high'
    for pattern in medium_patterns:
        if pattern in error_message:
            return 'medium'
    return 'low'


# ============================================================
# ⚙️ የውሂብ መላክ ማሻሻያ (Token Optimization & Safe JSON)
# ============================================================

def get_doctor_code_context(project_code, target_file_key=None, max_chars=3000):
    """
    ለኤአይ የሚላከውን የኮድ መጠን በጥንቃቄ ያሳጥራል።
    የስህተት መነሻ የሆነውን ፋይል ሙሉ በሙሉ ይልካል፣ ሌሎችን ግን ያሳጥራል።
    ይህም ትልቅ JSON ተቆርጦ ኤአይ እንዳይቋረጥ ይከላከላል።
    """
    optimized = {}
    for key, content in project_code.items():
        if not isinstance(content, str):
            optimized[key] = content
            continue
        
        if target_file_key and key == target_file_key:
            optimized[key] = content[:max_chars] + ("\n... [Truncated for AI size safety]" if len(content) > max_chars else "")
        else:
            lines = content.split('\n')
            if len(lines) > 30:
                optimized[key] = "\n".join(lines[:30]) + f"\n... [Truncated {len(lines)-30} lines to save tokens]"
            else:
                optimized[key] = content
    return optimized


# ============================================================
# 2. Doctor Memory (RAG for Self-Healing)
# ============================================================

class DoctorMemory:
    """ራስ-ሐኪም ትውስታ — ያለፉ ስህተቶችን እና መፍትሄዎችን ያስታውሳል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def remember_diagnosis(self, error_type, error_message, diagnosis, solution, success=True, confidence=80):
        """የተሳካ ምርመራ ያስታውሳል"""
        try:
            memory = VectorMemory.objects.create(
                memory_type='solution' if success else 'error',
                content=f"Error: {error_message[:200]}\nDiagnosis: {diagnosis[:300]}\nSolution: {solution[:500]}",
                metadata={
                    'error_type': error_type,
                    'success': success,
                    'confidence': confidence,
                    'site_id': self.site.id if self.site else None,
                    'timestamp': timezone.now().isoformat()
                },
                site=self.site,
                success_rate=float(confidence) if success else 0.0
            )
            memory.mark_used(success)
            logger.info(f"🧠 Remembered diagnosis for {error_type} (success={success})")
            return memory
        except Exception as e:
            logger.error(f"Failed to remember diagnosis: {e}")
            return None
    
    def find_similar_error(self, error_message, limit=3):
        """ተመሳሳይ ስህተቶችን ያገኛል"""
        try:
            return VectorMemory.find_similar(
                query=error_message,
                memory_type='error',
                site=self.site,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to find similar error: {e}")
            return []
    
    def find_similar_solution(self, error_message, limit=3):
        """ተመሳሳይ መፍትሄዎችን ያገኛል"""
        try:
            return VectorMemory.find_similar(
                query=error_message,
                memory_type='solution',
                site=self.site,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to find similar solution: {e}")
            return []


# ============================================================
# 3. Predictive Error Analyzer
# ============================================================

class PredictiveErrorAnalyzer:
    """ስህተቶችን በመተንበይ ለመከላከል ይረዳል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def analyze_error_patterns(self):
        """የስህተት ቅጦችን ይተነትናል"""
        errors = AgentErrorLog.objects.filter(site=self.site) if self.site else AgentErrorLog.objects.all()
        
        patterns = {
            'total_errors': errors.count(),
            'by_type': {},
            'by_site': {},
            'trend': 'stable',
            'most_common': None,
            'most_common_count': 0
        }
        
        for error_type, _ in AgentErrorLog.ERROR_TYPES:
            count = errors.filter(error_type=error_type).count()
            if count > 0:
                patterns['by_type'][error_type] = count
                if count > patterns['most_common_count']:
                    patterns['most_common'] = error_type
                    patterns['most_common_count'] = count
        
        if not self.site:
            sites = SiteRegistry.objects.filter(is_active=True)
            for site in sites:
                count = AgentErrorLog.objects.filter(site=site, resolved=False).count()
                if count > 0:
                    patterns['by_site'][site.name] = count
        
        week_ago = timezone.now() - timezone.timedelta(days=7)
        month_ago = timezone.now() - timezone.timedelta(days=30)
        
        week_errors = errors.filter(created_at__gte=week_ago).count()
        month_errors = errors.filter(created_at__gte=month_ago).count()
        
        if month_errors > 0:
            weekly_avg = month_errors / 4
            if week_errors > weekly_avg * 1.5:
                patterns['trend'] = 'increasing'
            elif week_errors < weekly_avg * 0.5:
                patterns['trend'] = 'decreasing'
        
        return patterns
    
    def predict_next_error(self):
        """የሚቀጥለውን ስህተት ይተነብያል"""
        patterns = self.analyze_error_patterns()
        
        if not patterns['by_type']:
            return None
        
        most_common = patterns['most_common']
        count = patterns['most_common_count']
        confidence = min(90, 50 + (count * 5))
        
        try:
            prediction = PredictionLog.objects.create(
                prediction_type='growth',
                predicted_value=float(count),
                confidence_score=float(confidence),
                input_data={
                    'most_common_error': most_common,
                    'trend': patterns['trend'],
                    'total_errors': patterns['total_errors']
                },
                site=self.site
            )
            
            return {
                'predicted_error': most_common,
                'confidence': confidence,
                'trend': patterns['trend'],
                'prediction_id': prediction.id
            }
        except Exception as e:
            logger.error(f"Failed to create prediction: {e}")
            return None


# ============================================================
# 4. External API Health Check
# ============================================================

class ExternalAPIHealthCheck:
    """የውጭ API ጤና ሁኔታን ይፈትሻል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def check_all_apis(self):
        """ሁሉንም ኤፒአዮች ይፈትሻል"""
        results = {}
        try:
            apis = ExternalAPI.objects.filter(site=self.site) if self.site else ExternalAPI.objects.all()
            
            for api in apis:
                results[api.name] = {
                    'status': api.status,
                    'calls_made': api.calls_made,
                    'rate_limit': api.rate_limit,
                    'health': 'good' if api.status == 'active' else 'warning',
                    'api_type': api.api_type
                }
        except Exception as e:
            logger.error(f"Failed to check APIs: {e}")
        
        return results


# ============================================================
# 5. የዲዛይን ጥገና እና ዝግመተ-ለውጥ
# ============================================================

def discover_and_heal_ui_design(current_theme_color, trend_context="Modern Minimalist", site=None):
    """አዳዲስና የተሻሉ የዲዛይን ስታይሎችን ያሰሳል፣ ስህተቶች ሲኖሩም ያክማል።"""
    site_name = site.name if site else "primary"
    style_key = f"DESIGN_STYLE_{slugify(trend_context)}_{slugify(site_name)}"
    
    try:
        cached_style = SiteConfig.objects.filter(key=style_key).first()
        if cached_style and cached_style.value:
            logger.info(f"🧠 Memory Match Found for Design Style ({site_name})!")
            return cached_style.value
    except Exception as e:
        logger.warning(f"Failed to get cached style: {e}")

    site_context = ""
    if site:
        site_context = f"""
        Site Information:
        - Name: {site.name}
        - Niche: {site.niche}
        - Target Market: {site.target_market}
        - Target Audience: {site.target_audience}
        """
    
    prompt = f"""
    [CRITICAL DIRECTIVE]
    You are the Chief UI/UX Architect of EthAfri.
    Current Theme Color: {current_theme_color}
    Target Trend Direction: {trend_context}
    {site_context}

    Task:
    Generate an optimized CSS variable block and smart design adjustments to enhance the visual appeal.
    Ensure to fix any common scaling or border-radius overflow bugs on product cards.

    Output Constraint:
    Return ONLY a valid JSON string with exactly two keys: 'theme_color' and 'custom_css'. 
    Do NOT include markdown. Just the raw JSON object.
    """
    
    try:
        ai_response = ask_ethafri_ceo(prompt, pool_type="coding")
        
        if not ai_response:
            raise ValueError("No AI response")
        
        if isinstance(ai_response, dict):
            design_data = ai_response
        else:
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON in AI response.")
            clean_json = ai_response[start_idx:end_idx]
            design_data = json.loads(clean_json)
        
        if design_data.get('custom_css'):
            validate_css_syntax(design_data['custom_css'])
        
        SiteConfig.objects.update_or_create(
            key=style_key,
            defaults={'value': design_data}
        )
        
        SelfHealingLog.objects.create(
            error_message=f"UI_EVOLUTION: Applied {trend_context} style for {site_name}",
            solution_sql=design_data.get('custom_css', '')[:500],
            resolved=True
        )
        logger.info(f"✅ UI Design updated for {site_name}")
        return design_data

    except Exception as ui_err:
        logger.error(f"❌ UI Healing/Evolution Failed for {site_name}: {ui_err}")
        return {
            "theme_color": current_theme_color,
            "custom_css": f":root {{ --primary-color: {current_theme_color}; }}"
        }


# ============================================================
# 6. የተሻሻለ ለአንድ ጣቢያ ስህተት ጥገና (Smart Single Site Healing)
# ============================================================

def heal_single_site_error(site: SiteRegistry, error_category, error_msg, target_context=None):
    """ለአንድ የተወሰነ ጣቢያ ስህተት ያስተካክላል"""
    site_name = site.name
    general_error = generalize_error_message(error_msg)
    severity = detect_error_severity(error_msg)
    
    logger.info(f"🩺 Starting healing for {site_name} - {error_category} (Severity: {severity})")
    
    doctor_memory = DoctorMemory(site)
    similar_solutions = doctor_memory.find_similar_solution(error_msg, limit=2)
    similar_errors = doctor_memory.find_similar_error(error_msg, limit=2)
    
    memory_context = ""
    for sol in similar_solutions:
        memory_context += f"\nPrevious solution: {sol.content[:200]}\n"
    
    error_context = ""
    for err in similar_errors:
        error_context += f"\nSimilar error: {err.content[:150]}\n"
    
    # የቆየ መፍትሄ ፍለጋ
    try:
        past_solution = SelfHealingLog.objects.filter(
            error_message__icontains=general_error[:150], 
            resolved=True
        ).order_by('-created_at').first()
        
        if past_solution and past_solution.solution_sql:
            logger.info(f"🧠 Memory Match Found for Error on {site_name}! Applying Cached Solution...")
            if error_category == 'DATABASE':
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(past_solution.solution_sql)
                    return f"✅ Database Healed for {site_name} using Local Memory!"
                except Exception as e:
                    logger.warning(f"Failed to apply cached SQL solution: {e}")
            elif error_category == 'CODE_EXECUTION':
                # የኮድ ስህተት ከሆነ በፋይል ላይ መጻፍ አለበት
                # የፋይል ስም ፈልግ
                target_file_key = 'views'
                project_code, file_paths = get_site_project_state(site)
                for key in file_paths.keys():
                    if key in error_msg.lower() or (target_context and key in str(target_context).lower()):
                        target_file_key = key
                        break
                
                path = file_paths.get(target_file_key)
                if path:
                    apply_code_change(
                        site=site,
                        file_key=target_file_key,
                        new_content=past_solution.solution_sql,
                        path=path,
                        reason=f"Auto-Heal (Memory): Fixed {target_file_key}",
                        confidence_score=95,
                        push_to_github=True
                    )
                    return f"✅ Code Healed for {site_name} on {target_file_key} using Memory!"
    except Exception as e:
        logger.warning(f"Failed to check past solution: {e}")

    try:
        project_code, file_paths = get_site_project_state(site)
    except Exception as e:
        logger.error(f"Failed to get project state: {e}")
        project_code, file_paths = {}, {}
    
    # የስህተት መነሻ ፋይል ፈልግ
    target_file_key = 'views'
    for key in file_paths.keys():
        if key in error_msg.lower() or (target_context and key in str(target_context).lower()):
            target_file_key = key
            break
            
    optimized_code = get_doctor_code_context(project_code, target_file_key=target_file_key)
    
    predictor = PredictiveErrorAnalyzer(site)
    prediction = predictor.predict_next_error()
    prediction_context = ""
    if prediction:
        prediction_context = f"Predicted error: {prediction['predicted_error']} ({prediction['confidence']}% confidence)"
    
    api_health = ExternalAPIHealthCheck(site)
    api_status = api_health.check_all_apis()
    api_context = f"API Status: {json.dumps(api_status, indent=2)}"
    
    if error_category == 'DATABASE':
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Smart Database Doctor for site: {site_name}.
        Error: {error_msg} 
        Context: {target_context}. 
        Memory Solution: {memory_context}
        Similar Errors: {error_context}
        Prediction: {prediction_context}
        {api_context}
        
        Return ONLY raw SQL statements to fix the issue. No explanations or markdown.
        """
    else:
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Smart Systems Engineer for site: {site_name}.
        Error: {error_msg} 
        Context: {target_context}. 
        Target File: {target_file_key}
        Memory Solution: {memory_context}
        Similar Errors: {error_context}
        Prediction: {prediction_context}
        {api_context}
        
        Current Codebase (Optimized):
        {json.dumps(optimized_code, indent=2)}
        
        Return ONLY the corrected raw Python code. No explanations or markdown.
        """

    try:
        ai_response = ask_ethafri_ceo(prompt, pool_type="healing")
        if not ai_response:
            return f"❌ AI Failover chain failed for {site_name}."
        
        clean_solution = extract_code_from_response(ai_response)
        
        if not clean_solution:
            return f"❌ No solution extracted for {site_name}."
        
        # መፍትሄውን መተግበር
        if error_category == 'DATABASE':
            try:
                with connection.cursor() as cursor:
                    cursor.execute(clean_solution)
            except Exception as db_err:
                logger.error(f"Database execution error: {db_err}")
                return f"❌ Database execution failed for {site_name}: {db_err}"
                
        elif error_category == 'CODE_EXECUTION':
            try:
                compile(clean_solution, '<string>', 'exec')
            except SyntaxError as syn_err:
                logger.error(f"Syntax error in solution: {syn_err}")
                return f"❌ Syntax error in solution for {site_name}: {syn_err}"
            
            # ✅ አመክንዮ ስህተት መፍትሄ፦ የሲንታክስ ምርመራ ካለፈ ኮዱን በፋይል ላይ መጻፍ አለበት!
            path = file_paths.get(target_file_key)
            if path:
                apply_code_change(
                    site=site,
                    file_key=target_file_key,
                    new_content=clean_solution,
                    path=path,
                    reason=f"Smart Doctor: Fixed {error_category} on {target_file_key}",
                    confidence_score=85,
                    push_to_github=True
                )
                logger.info(f"💾 Applied code fix to file: {path}")

        doctor_memory.remember_diagnosis(
            error_type=error_category,
            error_message=error_msg[:200],
            diagnosis=f"Fixed {error_category} error",
            solution=clean_solution[:500],
            success=True,
            confidence=85
        )

        SelfHealingLog.objects.create(
            error_message=general_error[:500],
            solution_sql=clean_solution,
            resolved=True
        )
        
        AgentErrorLog.objects.filter(
            site=site, 
            error_message__icontains=general_error[:100], 
            resolved=False
        ).update(resolved=True)
        
        try:
            PredictionLog.objects.create(
                prediction_type='growth',
                predicted_value=85.0,
                confidence_score=80.0,
                input_data={'site': site_name, 'error_type': error_category, 'healed': True},
                site=site
            )
        except Exception as e:
            logger.warning(f"Failed to create prediction log: {e}")
        
        return f"✅ Smart System Healed for {site_name}! Category: {error_category}"

    except Exception as heal_err:
        logger.error(f"❌ Auto-Healing Failed for {site_name}: {heal_err}")
        try:
            doctor_memory.remember_diagnosis(
                error_type=error_category,
                error_message=error_msg[:200],
                diagnosis=f"Failed with: {heal_err}",
                solution=clean_solution[:500] if 'clean_solution' in locals() else "",
                success=False,
                confidence=0
            )
        except Exception:
            pass
        
        SelfHealingLog.objects.create(
            error_message=f"Site: {site_name} | Error: {general_error[:200]} | Failed: {heal_err}",
            solution_sql=clean_solution[:500] if 'clean_solution' in locals() else "No solution generated",
            resolved=False
        )
        return f"❌ Auto-Healing Failed for {site_name}: {str(heal_err)}"


# ============================================================
# 7. ዋናው ስህተት ጥገና ተግባር (የተሻሻለ - Multi-Site)
# ============================================================

def heal_any_system_error(error_category, error_msg, target_context=None):
    """የዳታቤዝም ሆነ የኮድ አፈጻጸም ስህተቶች ሲከሰቱ ራሱን የሚያክም ዋና ሞተር"""
    results = []
    
    site_id = None
    if target_context:
        try:
            match = re.search(r'site_id[=:]\s*(\d+)', str(target_context))
            if match:
                site_id = int(match.group(1))
            
            site_name_match = re.search(r'site[_\s]+([a-zA-Z0-9_-]+)', str(target_context), re.IGNORECASE)
            if site_name_match:
                site_name = site_name_match.group(1)
        except Exception:
            pass
    
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception as e:
        logger.error(f"Failed to get active sites: {e}")
        return _heal_system_error_single(error_category, error_msg, target_context)
    
    if not sites.exists():
        return _heal_system_error_single(error_category, error_msg, target_context)
    
    if site_id:
        site = sites.filter(id=site_id).first()
        if site:
            try:
                result = heal_single_site_error(site, error_category, error_msg, target_context)
                return result
            finally:
                connection.close()
    
    if 'site_name' in locals() and site_name:
        site = sites.filter(name=site_name).first()
        if site:
            try:
                result = heal_single_site_error(site, error_category, error_msg, target_context)
                return result
            finally:
                connection.close()
    
    for site in sites:
        try:
            result = heal_single_site_error(site, error_category, error_msg, target_context)
            results.append(result)
        except Exception as e:
            error_msg_site = f"❌ Failed to heal {site.name}: {str(e)}"
            results.append(error_msg_site)
            logger.error(error_msg_site)
        finally:
            # ✅ የዳታቤዝ ግንኙነቶችን በጥንቃቄ መዝጋት (የዌብሳይት ፍጥነትን ያድናል)
            connection.close()
    
    if not results:
        return _heal_system_error_single(error_category, error_msg, target_context)
    
    return f"🛠️ Smart Multi-Site Heal Summary: {' | '.join(results)}"


# ============================================================
# 8. ነባሪ ጥገና ተግባር (ለአሮጌ ተኳሃኝነት)
# ============================================================

def _heal_system_error_single(error_category, error_msg, target_context=None):
    """የመጀመሪያው የስህተት ጥገና ተግባር (ለአሮጌ ተኳሃኝነት)"""
    general_error = generalize_error_message(error_msg)
    
    try:
        past_solution = SelfHealingLog.objects.filter(
            error_message__icontains=general_error[:150], 
            resolved=True
        ).order_by('-created_at').first()
        
        if past_solution and past_solution.solution_sql:
            logger.info(f"🧠 Memory Match Found for Error! Applying Cached Solution...")
            if error_category == 'DATABASE':
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(past_solution.solution_sql)
                    return "✅ Database Healed using Local Memory!"
                except Exception as e:
                    logger.warning(f"Failed to apply cached solution: {e}")
            elif error_category == 'CODE_EXECUTION':
                return past_solution.solution_sql
    except Exception as e:
        logger.warning(f"Failed to check past solution: {e}")

    if error_category == 'DATABASE':
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Autonomous Database Doctor of EthAfri. 
        Fix this PostgreSQL error: {error_msg} 
        For query/context: {target_context}. 
        Return ONLY raw SQL statements to fix the issue. No explanations or markdown.
        """
    else:
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Lead Systems Engineer of EthAfri. 
        Fix this Python runtime error: {error_msg} 
        In context: {target_context}. 
        Return ONLY the corrected raw Python code. No explanations or markdown.
        """

    try:
        ai_response = ask_ethafri_ceo(prompt, pool_type="healing")
        if not ai_response:
            return "❌ AI Failover chain failed."
        
        clean_solution = extract_code_from_response(ai_response)
        
        if not clean_solution:
            return "❌ No solution extracted from AI response."

        if error_category == 'DATABASE':
            with connection.cursor() as cursor:
                cursor.execute(clean_solution)
        elif error_category == 'CODE_EXECUTION':
            compile(clean_solution, '<string>', 'exec')

        SelfHealingLog.objects.create(
            error_message=general_error[:500],
            solution_sql=clean_solution,
            resolved=True
        )
        return f"✅ System Automatically Healed! Category: {error_category}"

    except Exception as heal_err:
        SelfHealingLog.objects.create(
            error_message=f"Category: {error_category} | Error: {general_error[:200]} | Failed: {heal_err}",
            solution_sql=clean_solution[:500] if 'clean_solution' in locals() else "No solution generated",
            resolved=False
        )
        return f"❌ Auto-Healing Failed: {str(heal_err)}"
    finally:
        connection.close()
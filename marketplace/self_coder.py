# EthAfri/marketplace/self_coder.py

import requests
import json
import base64
import re
import logging
from django.conf import settings
from .growth_agent import ask_ethafri_ceo 

logger = logging.getLogger(__name__)

def get_render_deploy_status():
    """የሬንደርን የቅርብ ጊዜ መጫን ሂደት ሁኔታ ያነባል"""
    service_id = getattr(settings, 'RENDER_SERVICE_ID', None)
    api_key = getattr(settings, 'RENDER_API_KEY', None)
    
    # ቁልፎቹ ከሌሉ ስራውን ያለምንም ስህተት ያቆማል (የደህንነት ቼክ)
    if not service_id or not api_key:
        return None
        
    url = f"https://api.render.com/v1/services/{service_id}/deploys"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and len(response.json()) > 0:
            latest_deploy = response.json()[0]['deploy']
            return {
                "id": latest_deploy['id'],
                "status": latest_deploy['status'], # build_failed, live, etc.
                "commit_id": latest_deploy['commitId']
            }
    except Exception as e:
        print(f"Render API Error: {e}")
    return None

def push_code_to_github(file_path, file_content, commit_message):
    """የተጻፈውን አዲስ የፓይተን ኮድ በቀጥታ ወደ ጊትሃብ ይልካል (Push)"""
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = "Anwar-tad/Ethafri" # የአንተ የጊትሃብ አካውንት
    if not github_token:
        return "❌ GITHUB_TOKEN Missing from settings."

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. የድሮውን ፋይል SHA ማግኘት (ለማዘመን ያስፈልጋል)
    sha = ""
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code == 200:
        sha = res.json().get('sha', '')

    # 2. ፋይሉን በ Base64 ኢንኮድ ማድረግ (የጊትሃብ የደህንነት ህግ ነው)
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

    # 3. ወደ ጊትሃብ መግፋት (Push)
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha if sha else None,
        "branch": "main"
    }
    
    put_res = requests.put(url, headers=headers, json=payload, timeout=10)
    if put_res.status_code in [200, 201]:
        return "✅ Code Pushed to GitHub Successfully!"
    return f"❌ Push Failed: {put_res.text}"

def self_heal_failed_build():
    """ሬንደር ላይ ቢከሽፍ AIው ራሱ መዝገቡን አንብቦ ኮዱን የሚጠግንበት ዑደት"""
    status_info = get_render_deploy_status()
    if not status_info:
        return "Render Status Check Skipped (Keys missing)."

    # ሬንደር ላይ መጫኑ ከከሸፈ (build_failed) ራሱን የማከም ስራ ይጀምራል
    if status_info['status'] == "build_failed":
        print("⚠️ Render Build Failed! Starting Self-Correction...")
        
        # 🛡️ 1. AIው ምላሹን በ JSON format እንዲያዘጋጅ ፕሮምፕቱ ተሻሽሏል
        prompt = f"""
        [CRITICAL DIRECTIVE] 
        You are the Autonomous CEO of EthAfri. Your latest code deployment on Render has FAILED.
        The Render commit ID that caused the crash is: {status_info['commit_id']}.
        
        Task instructions:
        1. Scan and analyze recent logic in 'marketplace/growth_agent.py'.
        2. Identify syntax errors, unhandled exceptions, missing imports, or database connection leaks.
        3. Correct the bugs completely while strictly maintaining all existing system safety rules and quota limits.
        
        Output Constraint:
        Provide your response in a valid JSON format with a single key 'code' containing the complete, raw, production-ready Python code for 'marketplace/growth_agent.py'.
        Example:
        {{
           "code": "import json\\nimport os\\n..."
        }}
        """
        
        ai_response = ask_ethafri_ceo(prompt)
        if not ai_response:
            return "❌ Self-Healing Failed: No response from AI."

        # 🛡️ 2. Dictionary/String ዓይነት ፍተሻ (AttributeError መከላከያ)
        raw_code = ""
        if isinstance(ai_response, dict):
            if "error" in ai_response:
                return f"❌ Self-Healing Skipped: AI failover returned error: {ai_response['error']}"
            # የኮድ ፋይሉን ከቁልፎች ውስጥ ፈልቅቆ ማውጣት
            raw_code = (
                ai_response.get('code') or 
                ai_response.get('solution') or 
                list(ai_response.values())[0]
            )
        else:
            raw_code = ai_response

        if not raw_code or len(raw_code.strip()) < 100:
            return "❌ Self-Healing Aborted: Extracted code is too short or empty."

        # የ AI ማርክዳውን ማጽጃ ማጠናከሪያ (Regex)
        clean_code = re.sub(r'^```[pP]ython\s*|^```\s*|```$', '', raw_code.strip(), flags=re.MULTILINE).strip()
        
        # 🛡️ 3. የሲንታክስ ምርመራ ምርመራ (Uptime Protection - compile test before GitHub push!)
        try:
            compile(clean_code, 'test_growth_agent.py', 'exec')
            print("✅ Self-Healed code passed compilation test! Safe to push.")
        except SyntaxError as syntax_err:
            return f"❌ Self-Healing Aborted: AI generated invalid Python code: {syntax_err}"
        
        # 4. የተስተካከለውን ኮድ በቀጥታ ወደ ጊትሃብ መግፋት (Push)
        push_result = push_code_to_github(
            "marketplace/growth_agent.py", 
            clean_code, 
            f"AI: Self-Corrected Build Error on Commit {status_info['commit_id'][:7]}"
        )
        return f"Heal Attempted: {push_result}"
            
    return f"System status is normal: {status_info['status']}"
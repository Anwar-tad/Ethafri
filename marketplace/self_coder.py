# EthAfri/marketplace/self_coder.py

import requests
import json
import base64
from django.conf import settings
from .growth_agent import ask_ethafri_brain

def get_render_deploy_status():
    """የሬንደርን የቅርብ ጊዜ መጫን ሂደት ሁኔታ ያነባል"""
    service_id = getattr(settings, 'RENDER_SERVICE_ID', None)
    api_key = getattr(settings, 'RENDER_API_KEY', None)
    if not service_id or not api_key:
        return None
        
    url = f"https://api.render.com/v1/services/{service_id}/deploys"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
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
        return "❌ GITHUB_TOKEN አልተገኘም"

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. የድሮውን ፋይል SHA ማግኘት (ለማዘመን ያስፈልጋል)
    sha = ""
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code == 200:
        sha = res.json()['sha']

    # 2. ፋይሉን በ Base64 ኢንኮድ ማድረግ
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
        return "No status retrieved."

    if status_info['status'] == "build_failed":
        print("⚠️ Render Build Failed! Starting Self-Correction...")
        
        # 1. ስህተቱን ለ AI ማብራራት
        # (እዚህ ጋር የሬንደርን ስህተት መዝገብ አውርዶ እንዲያነበው እናደርገዋለን)
        prompt = f"""
        አንተ የ EthAfri ራስ-ገዝ CEO ነህ። የጻፍከው የቅርብ ጊዜ ኮድ ሬንደር ሰርቨር ላይ ሲጫን 'Build Failed' ሆኗል።
        የከሸፈው የኮሚት መለያ (Commit ID) ይህ ነው፦ {status_info['commit_id']}
        
        እባክህ የጻፍከውን ኮድ እና በዳታቤዝ ውስጥ ያሉትን የቅርብ ጊዜ የኮድ ለውጦች መርምረህ ስህተቱን አስተካክል።
        የተስተካከለውን ሙሉ የፓይተን ኮድ ብቻ ስጠኝ።
        """
        
        corrected_code = ask_ethafri_brain(prompt)
        if corrected_code:
            # 2. የተስተካከለውን ኮድ በቀጥታ ወደ ጊትሃብ መግፋት (ይህ ሬንደርን በራሱ መልሶ እንዲጭን ያደርገዋል)
            push_result = push_code_to_github("marketplace/growth_agent.py", corrected_code, "AI: Self-Corrected Build Error")
            return f"Heal Attempted: {push_result}"
            
    return f"System status is normal: {status_info['status']}"
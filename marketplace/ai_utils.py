# ============================================================
# 🧠 TASK-BASED AI ROUTER WITH GEMINI KEY ROTATOR
# ============================================================

def _get_priority_providers(task_type: str) -> List[str]:
    """
    በታስኩ ዓይነት (Task Type) መሠረት ምርጥ የሆኑትን የ AI አቅራቢዎች
    ቅደም-ተከተል በዳይናሚክ መንገድ የሚወስን የስራ ክፍፍል ማዕከል [1]።
    """
    # 1. የትርጉምና የሲስተም ትንተና ስራዎች በቅድሚያ ለጌሚኒ ይሰጣሉ
    if task_type in ["translation", "analysis", "critical"]:
        return ["GEMINI", "HUGGINGFACE", "GITHUB", "MISTRAL"]
        
    # 2. የኮድ አጻጻፍ እና ራስ-ዝግመተ ለውጥ ለ GitHub/HuggingFace ይሰጣሉ (ቶከን ለመቆጠብ)
    elif task_type in ["coding", "self_evolution"]:
        return ["GITHUB", "HUGGINGFACE", "MISTRAL", "GEMINI"]
        
    # 3. የይዘት ማጣሪያዎች እና የ SEO ስራዎች ለ ፈጣኑ ግሮቅ ይሰጣሉ
    elif task_type in ["seo", "curation", "spam_filter"]:
        return ["GROQ", "OPENROUTER", "MISTRAL"]
        
    # 4. የገበያ ጥናቶች ለ ሚስትረል ይሰጣሉ
    elif task_type == "market_research":
        return ["MISTRAL", "GEMINI", "OPENROUTER"]
        
    # የዲፎልት ቅደም-ተከተል
    return ["GEMINI", "GROQ", "MISTRAL", "OPENROUTER", "HUGGINGFACE", "GITHUB"]


def ask_master_ai_smart(prompt: str, task_type: str = "analysis", system_instruction: str = "", task=None) -> str:
    """
    የ 9ኙን የኤአይ ቁልፎች የሥራ ክፍፍል በታስኩ ዓይነት (Task Type) የሚመራ፣
    እና በ 4ቱ የጌሚኒ ቁልፎች መካከል በራስ-ሰር የሚያሽከረክር የላቀ ሮውተር [1]።
    """
    quota_lock = cache.get("ai_quota_locked_until")
    if quota_lock:
        logger.warning(f"⚠️ AI Router: Blocked until {quota_lock} due to global lockout.")
        return "{}"
    
    prompt_compressed = AIUtils.compress_code_for_prompt(prompt)
    
    # 1. በታስኩ ዓይነት መሠረት የአቅራቢዎችን ቅድሚያ ዝርዝር ማግኘት
    providers_order = _get_priority_providers(task_type)
    
    last_error = ""
    for provider in providers_order:
        api_keys = []
        
        # 2. አቅራቢው GEMINI ከሆነ በ 4ቱ የጌሚኒ ቁልፎች መካከል ማሽከርከር (Gemini Rotator) [1]
        if provider == "GEMINI":
            gemini_keys = [
                os.getenv('GEMINI_API_KEY', ''),
                os.getenv('GEMINI_API_KEY_2', ''),
                os.getenv('GEMINI_API_KEY_3', ''),
                os.getenv('GEMINI_API_KEY_4', '')
            ]
            api_keys = [k.strip().replace('"', '').replace("'", "") for k in gemini_keys if k]
        else:
            key_name = f"{provider}_API_KEY" if provider != "GITHUB" else "GITHUB_TOKEN"
            raw_key = os.getenv(key_name, '')
            if raw_key:
                api_keys = [raw_key.strip().replace('"', '').replace("'", "")]
                
        if not api_keys:
            continue
            
        # ለእያንዳንዱ አቅራቢ ጥሪዎችን በደህንነት ማስፈጸም
        for idx, api_key in enumerate(api_keys):
            provider_tag = f"{provider}_KEY_{idx+1}" if provider == "GEMINI" else provider
            url, headers, payload_builder = _detect_and_route_provider_specs(provider, api_key)
            
            # 3. ADAPTIVE PACING: የ GitHub ወይም HuggingFace የጥሪ ጊዜዎችን ማፈራረቅ
            if provider in ["GITHUB", "HUGGINGFACE"]:
                sleep_time = random.uniform(1.5, 3.5)
                time.sleep(sleep_time)
                
            try:
                payload = payload_builder(prompt_compressed, system_instruction)
                res = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if res.status_code == 429:
                    logger.warning(f"⚠️ {provider_tag} hit rate limit (429). Trying next fallback...")
                    continue
                    
                if res.status_code == 200:
                    response_data = res.json()
                    return _parse_provider_response(provider, response_data)
                    
                last_error = f"HTTP {res.status_code}: {res.text}"
                logger.warning(f"⚠️ {provider_tag} failed with {last_error}. Trying next fallback...")
                
            except requests.exceptions.Timeout:
                last_error = f"Timeout (10s) reached for {provider_tag}"
                logger.warning(f"⏱️ Fail-Fast: {provider_tag} timed out. Swapping...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ Connection to {provider_tag} failed: {e}. Swapping...")
                
    logger.error(f"❌ AI Router: All 9 configured keys exhausted. Last error: {last_error}")
    return "{}"


def _detect_and_route_provider_specs(provider: str, api_key: str) -> Tuple[str, Dict[str, str], Any]:
    """አቅራቢዎችን በመለየት ትክክለኛውን URL እና Payload ማመንጫ ይወስናል [1]"""
    headers = {"Content-Type": "application/json"}
    
    if provider == "GITHUB":
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "meta-llama-3.1-8b-instruct",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "HUGGINGFACE":
        url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "inputs": f"<|system|>\n{s}\n<|user|>\n{p}\n<|assistant|>\n"
        }
        
    elif provider == "GROQ":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "MISTRAL":
        url = "https://api.mistral.ai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "mistral-small-latest",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "OPENROUTER":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "meta-llama/llama-3-8b-instruct:free",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    # GEMINI Fallback
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    return url, headers, lambda p, s: {
        "contents": [{"parts": [{"text": f"{s}\n\n{p}"}]}]
    }


def _parse_provider_response(provider: str, response_data: Any) -> str:
    """የእያንዳንዱን አቅራቢ የውሂብ ምላሽ በትክክል ይተረጉማል [1]"""
    if provider == "GEMINI":
        return response_data['candidates'][0]['content']['parts'][0]['text']
    elif provider in ["GITHUB", "GROQ", "MISTRAL", "OPENROUTER"]:
        return response_data['choices'][0]['message']['content']
    elif provider == "HUGGINGFACE":
        if isinstance(response_data, list) and len(response_data) > 0:
            gen_text = response_data[0].get('generated_text', '')
            if '<|assistant|>\n' in gen_text:
                return gen_text.split('<|assistant|>\n')[-1].strip()
            return gen_text.strip()
    return "{}"
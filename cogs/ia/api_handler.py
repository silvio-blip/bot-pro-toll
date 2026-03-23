import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("🤖 API HANDLER")


class APIHandler:
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=120)

    def detect_provider(self, api_url: str) -> Tuple[str, str]:
        api_url_lower = api_url.lower().strip()
        
        if "openai.com" in api_url_lower or "api.openai.com" in api_url_lower:
            return "openai", "https://api.openai.com/v1"
        elif "anthropic.com" in api_url_lower or "api.anthropic.com" in api_url_lower:
            return "anthropic", "https://api.anthropic.com"
        elif "googleapis.com" in api_url_lower or "generativelanguage.googleapis" in api_url_lower:
            return "google", "https://generativelanguage.googleapis.com/v1beta"
        elif "cohere.ai" in api_url_lower or "api.cohere.ai" in api_url_lower:
            return "cohere", "https://api.cohere.ai/v1"
        elif "azure.com" in api_url_lower or "openai.azure.com" in api_url_lower:
            return "azure", api_url.split("/openai")[0] if "/openai" in api_url else api_url
        elif "ollama" in api_url_lower or "localhost" in api_url_lower:
            return "ollama", api_url.rstrip("/")
        elif "together.ai" in api_url_lower or "api.together.xyz" in api_url_lower:
            return "together", "https://api.together.xyz/v1"
        elif "mistral.ai" in api_url_lower or "api.mistral.ai" in api_url_lower:
            return "mistral", "https://api.mistral.ai/v1"
        elif "perplexity.ai" in api_url_lower or "api.perplexity.ai" in api_url_lower:
            return "perplexity", "https://api.perplexity.ai"
        elif "groq.com" in api_url_lower or "api.groq.com" in api_url_lower:
            return "groq", "https://api.groq.com/openai/v1"
        elif "deepseek.com" in api_url_lower or "api.deepseek.com" in api_url_lower:
            return "deepseek", "https://api.deepseek.com/v1"
        elif "openrouter.ai" in api_url_lower or "openrouterapi" in api_url_lower:
            return "openrouter", "https://openrouter.ai/api/v1"
        elif "fireworks.ai" in api_url_lower or "api.fireworks.ai" in api_url_lower:
            return "fireworks", "https://api.fireworks.ai/v1"
        elif "anyscale" in api_url_lower or "api.endpoints.anyscale" in api_url_lower:
            return "anyscale", "https://api.endpoints.anyscale.com/v1"
        elif "replicate" in api_url_lower or "api.replicate.com" in api_url_lower:
            return "replicate", "https://api.replicate.com/v1"
        elif "cloudflare" in api_url_lower or "api.cloudflare.com" in api_url_lower:
            return "cloudflare", api_url.rstrip("/")
        elif "sambanova" in api_url_lower or "api.sambanova" in api_url_lower:
            return "sambanova", "https://api.sambanova.ai/v1"
        elif "novita" in api_url_lower or "api.novita.ai" in api_url_lower:
            return "novita", "https://api.novita.ai/v1"
        elif "hyperbolic" in api_url_lower or "api.hyperbolic.ai" in api_url_lower:
            return "hyperbolic", "https://api.hyperbolic.ai/v1"
        elif "cerebras" in api_url_lower or "api.cerebras.ai" in api_url_lower:
            return "cerebras", "https://api.cerebras.ai/v1"
        else:
            return "custom", api_url.rstrip("/").rstrip("/v1").rstrip("/v")

    async def validate_and_list_models(self, api_url: str, api_key: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        provider, base_url = self.detect_provider(api_url)
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        try:
            if provider == "openai":
                return await self._list_openai_models(base_url, headers)
            elif provider == "anthropic":
                return await self._list_anthropic_models(base_url, api_key)
            elif provider == "google":
                return await self._list_google_models(api_url, api_key)
            elif provider == "azure":
                return await self._list_azure_models(api_url, api_key)
            elif provider == "ollama":
                return await self._list_ollama_models(base_url)
            elif provider in ["together", "cohere", "mistral", "perplexity", "groq", "deepseek", "openrouter", "fireworks", "anyscale", "sambanova", "novita", "hyperbolic", "cerebras"]:
                return await self._list_openai_compatible_models(base_url, headers, provider)
            elif provider == "replicate":
                return await self._list_replicate_models(base_url, headers)
            elif provider == "cloudflare":
                return await self._list_cloudflare_models(api_url, api_key)
            else:
                return False, f"Provedor não reconhecido: {provider}", None
                
        except Exception as e:
            logging.error(f"[❌] Erro ao validar API: {e}")
            return False, f"Erro ao conectar com a API: {str(e)}", None

    async def _list_openai_compatible_models(self, base_url: str, headers: Dict, provider: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{base_url}/models", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        return True, None, models
                    elif resp.status == 401:
                        return False, "API key inválida (Unauthorized)", None
                    elif resp.status == 429:
                        return False, "Quota excedida (Too Many Requests)", None
                    else:
                        text = await resp.text()
                        return False, f"Erro {resp.status}: {text[:100]}", None
            except aiohttp.ClientError as e:
                return False, f"Erro de conexão: {str(e)}", None

    async def _list_openai_models(self, base_url: str, headers: Dict) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        return await self._list_openai_compatible_models(base_url, headers, "openai")

    async def _list_anthropic_models(self, base_url: str, api_key: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{base_url}/models", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        return True, None, models
                    elif resp.status == 401:
                        return False, "API key inválida", None
                    else:
                        return False, f"Erro {resp.status}", None
            except Exception as e:
                return False, f"Erro: {str(e)}", None

    async def _list_google_models(self, api_url: str, api_key: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                base_url = api_url.split("/models")[0] if "/models" in api_url else api_url
                async with session.get(f"{base_url}/models?key={api_key}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"].split("/")[-1] for m in data.get("models", [])]
                        return True, None, models
                    else:
                        return False, f"Erro {resp.status}", None
            except Exception as e:
                return False, f"Erro: {str(e)}", None

    async def _list_azure_models(self, api_url: str, api_key: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        base_url = api_url.split("/deployments")[0] if "/deployments" in api_url else api_url
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{base_url}/models?api-version=2024-02-15-preview", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        return True, None, models
                    else:
                        return False, f"Erro {resp.status}", None
            except Exception as e:
                return False, f"Erro: {str(e)}", None

    async def _list_ollama_models(self, base_url: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return True, None, models
                    else:
                        return False, f"Erro {resp.status}", None
            except Exception as e:
                return False, f"Erro de conexão: {str(e)}", None

    async def send_message(self, api_url: str, api_key: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        provider, base_url = self.detect_provider(api_url)
        logging.info(f"[📤] Enviando mensagem | Provider: {provider} | Modelo: {model}")
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        try:
            if provider == "openai":
                return await self._send_openai_message(base_url, headers, model, messages, system_prompt)
            elif provider == "anthropic":
                return await self._send_anthropic_message(base_url, api_key, model, messages, system_prompt)
            elif provider == "google":
                return await self._send_google_message(api_url, api_key, model, messages, system_prompt)
            elif provider == "azure":
                return await self._send_azure_message(api_url, api_key, model, messages, system_prompt)
            elif provider == "ollama":
                return await self._send_ollama_message(base_url, model, messages, system_prompt)
            elif provider in ["together", "cohere", "mistral", "perplexity", "groq", "deepseek", "openrouter", "fireworks", "anyscale", "sambanova", "novita", "hyperbolic", "cerebras"]:
                return await self._send_openai_message(base_url, headers, model, messages, system_prompt)
            elif provider == "replicate":
                return await self._send_replicate_message(base_url, api_key, model, messages, system_prompt)
            elif provider == "cloudflare":
                return await self._send_cloudflare_message(api_url, api_key, model, messages, system_prompt)
            else:
                return False, f"Provedor não suportado: {provider}", None
                
        except Exception as e:
            logging.error(f"[❌] Erro ao enviar mensagem: {e}")
            return False, f"Erro ao processar resposta: {str(e)}", None

    async def _send_openai_message(self, base_url: str, headers: Dict, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        payload = {
            "model": model,
            "messages": messages.copy()
        }
        
        if system_prompt:
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] = system_prompt + "\n\n" + messages[0].get("content", "")
            else:
                messages.insert(0, {"role": "system", "content": system_prompt})
            payload["messages"] = messages
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{base_url}/chat/completions", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return True, None, content
                elif resp.status == 401:
                    return False, "API key inválida", None
                elif resp.status == 429:
                    return False, "Quota excedida. Limite de requisições atingido.", None
                elif resp.status == 400:
                    data = await resp.json()
                    error_msg = data.get("error", {}).get("message", "Erro na requisição")
                    return False, f"Erro: {error_msg}", None
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None

    async def _send_anthropic_message(self, base_url: str, api_key: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        system_content = system_prompt or ""
        chat_messages = [m for m in messages if m.get("role") != "system"]
        
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_content,
            "messages": chat_messages
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{base_url}/messages", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["content"][0]["text"]
                    return True, None, content
                elif resp.status == 401:
                    return False, "API key inválida", None
                elif resp.status == 429:
                    return False, "Quota excedida", None
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None

    async def _send_google_message(self, api_url: str, api_key: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        base_url = api_url.split("/generativeModels")[0] if "/generativeModels" in api_url else api_url
        
        contents = []
        for msg in messages:
            if msg.get("role") != "system":
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{base_url}/generativeModels/{model}:generateContent?key={api_key}"
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return True, None, content
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None

    async def _send_azure_message(self, api_url: str, api_key: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        azure_messages = messages.copy()
        if system_prompt:
            azure_messages.insert(0, {"role": "system", "content": system_prompt})
        
        deployment_name = model
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{api_url}/deployments/{deployment_name}/chat/completions?api-version=2024-02-15-preview", headers=headers, json={"messages": azure_messages}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return True, None, content
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None

    async def _send_ollama_message(self, base_url: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        ollama_messages = []
        
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            if msg.get("role") != "system":
                ollama_messages.append({"role": msg["role"], "content": msg["content"]})
        
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": False
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{base_url}/api/chat", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["message"]["content"]
                    return True, None, content
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None

    async def _list_replicate_models(self, base_url: str, headers: Dict) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(f"{base_url}/models", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return True, None, models
                    elif resp.status == 401:
                        return False, "API key inválida", None
                    else:
                        text = await resp.text()
                        return False, f"Erro {resp.status}: {text[:100]}", None
            except aiohttp.ClientError as e:
                return False, f"Erro de conexão: {str(e)}", None

    async def _list_cloudflare_models(self, api_url: str, api_key: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                async with session.get(f"{api_url}/models", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return True, None, models
                    elif resp.status == 401:
                        return False, "API key inválida", None
                    else:
                        text = await resp.text()
                        return False, f"Erro {resp.status}: {text[:100]}", None
            except aiohttp.ClientError as e:
                return False, f"Erro de conexão: {str(e)}", None

    async def _send_replicate_message(self, base_url: str, api_key: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        all_messages = messages.copy()
        if system_prompt:
            all_messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "version": model,
            "input": {
                "messages": all_messages,
                "prompt": "\n".join([f"{m['role']}: {m['content']}" for m in all_messages])
            }
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{base_url}/v1/predictions", headers=headers, json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    prediction_id = data.get("id")
                    
                    for _ in range(60):
                        await asyncio.sleep(2)
                        async with session.get(f"{base_url}/v1/predictions/{prediction_id}", headers=headers) as status_resp:
                            if status_resp.status == 200:
                                status_data = await status_resp.json()
                                if status_data.get("status") == "succeeded":
                                    output = status_data.get("output", [])
                                    if isinstance(output, list):
                                        content = output[0] if output else ""
                                    else:
                                        content = str(output)
                                    return True, None, content
                                elif status_data.get("status") == "failed":
                                    return False, "Predição falhou", None
                    return False, "Timeout aguardando resposta", None
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None

    async def _send_cloudflare_message(self, api_url: str, api_key: str, model: str, messages: List[Dict[str, str]], system_prompt: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        contents = []
        for msg in messages:
            if msg.get("role") != "system":
                role = "user" if msg["role"] == "user" else "assistant"
                contents.append({
                    "role": role,
                    "content": [{"text": msg["content"]}]
                })
        
        payload = {
            "model": model,
            "messages": contents,
            "max_tokens": 2048
        }
        
        if system_prompt:
            payload["system"] = [{"text": system_prompt}]
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(f"{api_url}/chat/completions", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return True, None, content
                elif resp.status == 401:
                    return False, "API key inválida", None
                elif resp.status == 429:
                    return False, "Quota excedida", None
                else:
                    text = await resp.text()
                    return False, f"Erro {resp.status}: {text[:200]}", None
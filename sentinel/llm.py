from __future__ import annotations

import json
import logging
import ssl
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, Union
from sentinel.config import config

logger = logging.getLogger("sentinel.llm")
SSL_CTX = ssl._create_unverified_context()

class LLMProvider:
    """Unified LLM client providing structured output reasoning."""

    def __init__(self) -> None:
        self.gemini_key = config.GEMINI_API_KEY
        self.gemini_model = config.GEMINI_MODEL
        self.cf_token = config.CLOUDFLARE_API_TOKEN
        self.cf_account = config.CLOUDFLARE_ACCOUNT_ID
        self.cf_model = config.CLOUDFLARE_AI_MODEL

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        fallback_data: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """Generate structured JSON output from LLM, with guaranteed fallback."""
        # 1. Try Gemini if key configured
        if self.gemini_key:
            try:
                res = self._call_gemini(prompt, system_prompt, temperature)
                parsed = self._extract_json(res)
                if parsed:
                    return parsed
            except Exception as e:
                logger.warning(f"Gemini call failed or parse error: {e}. Trying fallback.")

        # 2. Try Cloudflare Workers AI if configured
        if self.cf_token and self.cf_account:
            try:
                res = self._call_cloudflare_ai(prompt, system_prompt)
                parsed = self._extract_json(res)
                if parsed:
                    return parsed
            except Exception as e:
                logger.warning(f"Cloudflare AI call failed: {e}. Trying fallback.")

        # 3. Deterministic high-quality synthetic fallback
        if fallback_data is not None:
            return fallback_data

        return {"error": "No LLM provider available and no fallback provided"}

    def _call_gemini(
        self, prompt: str, system_prompt: Optional[str], temperature: float
    ) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.gemini_model}:generateContent?key={self.gemini_key}"
        )
        full_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        body = {
            "contents": [{"parts": [{"text": full_text}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
            data_resp = json.loads(resp.read().decode("utf-8"))
            candidates = data_resp.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return ""

    def _call_cloudflare_ai(self, prompt: str, system_prompt: Optional[str]) -> str:
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account}/ai/run/"
            f"{self.cf_model}"
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        req = urllib.request.Request(
            url,
            data=json.dumps({"messages": messages}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.cf_token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data_resp = json.loads(resp.read().decode("utf-8"))
            if data_resp.get("success"):
                return data_resp.get("result", {}).get("response", "")
        return ""

    def _extract_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        text = raw_text.strip()
        if not text:
            return None
        # Clean markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find balanced JSON braces
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except Exception:
                    pass
        return None

llm = LLMProvider()

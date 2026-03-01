from __future__ import annotations

import json
import logging
from typing import Iterator

from openai import OpenAI

from app.core.config import settings
from app.providers.base import ChatLLMResult, LLMProvider, MealVisionItem, MealVisionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是 MetaboDash 的健康AI助手 Dr.Dog 🐶。
你帮助用户理解血糖数据、饮食记录和代谢健康。

关键规则:
- 始终用中文回答
- 引用用户自身的数据时要具体、用数字说话
- 如果用户出现紧急症状,立刻建议就医
- 保持亲切、专业、简洁的风格
- 使用 Markdown 格式化回答（加粗、列表等）
- 回答结尾可以给 1-2 个后续建议问题
"""


def _build_messages(context: dict, user_query: str) -> list[dict]:
    """Build the messages array for OpenAI Chat Completions."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject user context as a system message
    ctx_parts = []
    if context.get("glucose"):
        g = context["glucose"]
        ctx_parts.append(f"血糖数据 (last_24h): avg={g.get('last_24h', {}).get('avg')}, "
                         f"TIR={g.get('last_24h', {}).get('tir_70_180_pct')}, "
                         f"variability={g.get('last_24h', {}).get('variability')}")
    if context.get("kcal_today") is not None:
        ctx_parts.append(f"今日热量: {context['kcal_today']} kcal")
    if context.get("meals_today"):
        meals = context["meals_today"]
        ctx_parts.append(f"今日进餐 {len(meals)} 次: " +
                         ", ".join(f"{m.get('kcal', '?')}kcal@{m.get('ts', '?')}" for m in meals))
    if context.get("agent_features"):
        ctx_parts.append(f"Agent特征: {json.dumps(context['agent_features'], ensure_ascii=False)}")
    if context.get("user_profile_info"):
        ctx_parts.append(f"用户画像: {json.dumps(context['user_profile_info'], ensure_ascii=False)}")

    if ctx_parts:
        messages.append({
            "role": "system",
            "content": "以下是该用户的实时健康数据:\n" + "\n".join(ctx_parts),
        })

    messages.append({"role": "user", "content": user_query})
    return messages


class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    text_model = settings.OPENAI_MODEL_TEXT
    vision_model = settings.OPENAI_MODEL_VISION

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def analyze_image(self, image_url: str) -> MealVisionResult:
        """Analyze a meal photo using GPT vision."""
        try:
            response = self._client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": "你是食物识别专家。分析图片中的食物,返回JSON格式: "
                     '{"items": [{"name": "食物名", "portion_text": "份量", "kcal": 数字}], '
                     '"total_kcal": 数字, "confidence": 0-1, "notes": "备注"}'},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": "请分析这张图片中的食物,估算热量。"},
                    ]},
                ],
                max_completion_tokens=500,
                temperature=0.3,
            )
            raw = response.choices[0].message.content or "{}"
            # Try to parse JSON from the response
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                if "```" in raw:
                    raw = raw.split("```json")[-1].split("```")[0].strip()
                    data = json.loads(raw)
                else:
                    raise

            items = [MealVisionItem(**item) for item in data.get("items", [])]
            return MealVisionResult(
                items=items,
                total_kcal=data.get("total_kcal", sum(i.kcal for i in items)),
                confidence=data.get("confidence", 0.5),
                notes=data.get("notes", ""),
            )
        except Exception as e:
            logger.error("OpenAI vision analysis failed: %s", e)
            items = [MealVisionItem(name="unknown meal", portion_text="1 serving", kcal=480)]
            return MealVisionResult(items=items, total_kcal=480, confidence=0.2,
                                    notes=f"Vision fallback: {e}")

    def generate_text(self, context: dict, user_query: str) -> ChatLLMResult:
        """Generate a complete text response."""
        try:
            messages = _build_messages(context, user_query)
            response = self._client.chat.completions.create(
                model=self.text_model,
                messages=messages,
                max_completion_tokens=1500,
                temperature=0.7,
            )
            answer = response.choices[0].message.content or ""
            return ChatLLMResult(
                answer_markdown=answer,
                confidence=0.85,
                followups=[],
                safety_flags=[],
            )
        except Exception as e:
            logger.error("OpenAI generate_text failed: %s", e)
            return ChatLLMResult(
                answer_markdown=f"抱歉，AI 暂时无法回答。错误信息: {e}",
                confidence=0.0,
                followups=["请稍后再试"],
                safety_flags=["provider_error"],
            )

    def stream_text(self, context: dict, user_query: str) -> Iterator[str]:
        """Stream text token-by-token using OpenAI streaming API."""
        try:
            messages = _build_messages(context, user_query)
            stream = self._client.chat.completions.create(
                model=self.text_model,
                messages=messages,
                max_completion_tokens=1500,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error("OpenAI stream_text failed: %s", e)
            yield f"\n\n⚠️ AI 流式响应失败: {e}"

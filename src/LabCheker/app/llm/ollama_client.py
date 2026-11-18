import json

import httpx


OLLAMA_URL = "http://localhost:11434/api/chat"

MODEL_NAME = "hf.co/sesaily/gemma-4-E4B-Frends-it-GGUF:Q4_K_M"

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "completed",
                            "not_completed",
                            "error",
                            "no_data"
                        ]
                    },
                    "explanation": {"type": "string"}
                },
                "required": [
                    "criterion",
                    "status",
                    "explanation"
                ]
            }
        },
        "summary": {"type": "string"}
    },
    "required": ["criteria", "summary"]
}

SYSTEM_PROMPT = """
Ты — экспертная система проверки лабораторных работ по программированию.

Твоя задача — ПРОАНАЛИЗИРОВАТЬ исходный код студента
и проверить каждый переданный критерий.

ВАЖНО:
1. Не пересказывай входные данные.
2. Не возвращай критерии и исходный код без анализа.
3. Для каждого критерия самостоятельно определи,
   выполнен он или нет.
4. Обоснуй каждый результат конкретными элементами кода.
5. Не выдумывай отсутствующую функциональность.

Допустимые статусы:
- completed
- not_completed
- error
- no_data

Верни строго JSON следующей структуры:

{
  "criteria": [
    {
      "criterion": "Название критерия",
      "status": "completed",
      "explanation": "Обоснование результата"
    }
  ],
  "summary": "Общий итог проверки"
}

В массиве criteria должно быть ровно столько элементов,
сколько критериев передано на вход.

Не добавляй никакого текста вне JSON.
"""


async def evaluate_code(
    criteria_markdown: str,
    source_code: str
) -> dict:
    user_message = f"""
    Выполни проверку лабораторной работы.

    === КРИТЕРИИ ===

    {criteria_markdown}

    === ИСХОДНЫЙ КОД ===

    {source_code}

    === ЗАДАНИЕ ===

    Проверь каждый критерий по исходному коду.
    Верни результат строго в указанном JSON-формате.
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "format": RESPONSE_SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json=payload
        )

        response.raise_for_status()

    response_data = response.json()

    content = response_data["message"]["content"]

    return json.loads(content)
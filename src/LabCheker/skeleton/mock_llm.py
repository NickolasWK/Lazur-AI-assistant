"""Точка замены заглушки на реальный вызов модели."""

import re


async def evaluate_code(criteria_markdown: str, source_code: str) -> dict:
    """Возвращает данные в формате существующего клиента, не анализируя код."""
    criteria = []
    for line in criteria_markdown.splitlines():
        match = re.match(r"^\s*(?:\d+[.)]|[-*+])\s+(.+)$", line)
        if match:
            criteria.append(match.group(1))
    if not criteria:
        criteria = ["Переданные критерии"]

    return {
        "criteria": [
            {
                "criterion": criterion,
                "status": "no_data",
                "explanation": "Результат по этому критерию пока не получен.",
            }
            for criterion in criteria
        ],
        "summary": (
            f"Работа получена: {len(source_code)} символов. "
            "Результаты проверки пока отсутствуют."
        ),
    }


def create_feedback(result: dict) -> str:
    lines = ["# Результат обработки работы", "", result["summary"], ""]
    for item in result["criteria"]:
        lines.extend([
            f"## {item['criterion']}",
            f"Статус: {item['status']}",
            item["explanation"],
            "",
        ])
    return "\n".join(lines)

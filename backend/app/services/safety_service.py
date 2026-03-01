EMERGENCY_KEYWORDS = [
    "胸痛",
    "昏厥",
    "呼吸困难",
    "意识模糊",
    "抽搐",
    "严重低血糖",
    "严重高血糖",
    "seizure",
    "faint",
    "chest pain",
    "shortness of breath",
]


def detect_safety_flags(user_message: str) -> list[str]:
    msg = user_message.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw.lower() in msg:
            return ["emergency_symptom"]
    return []


def emergency_template() -> str:
    return (
        "**重要提示：**你描述的情况可能需要及时医疗评估。\\n\\n"
        "- 如果症状严重或加重，请立即联系当地急救/就医。\\n"
        "- 如果你有已知糖尿病或用药史，请遵循医生给你的紧急处理方案。\\n"
        "- 你也可以告诉我：症状开始时间、是否伴随出汗/心慌/意识模糊、最近一次进食与血糖读数。"
    )

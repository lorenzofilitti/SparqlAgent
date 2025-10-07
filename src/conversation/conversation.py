

def format_conversation_history(user_message: str, assistant_message: str) -> list[dict]:
    msg_list = [
        { "role": "user", "content": user_message},
        { "role": "assistant", "content": assistant_message}
    ]
    return msg_list
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from app.models.schemas import ChatMessage


class ConversationStore:
    def __init__(self, max_messages: int = 12):
        self._sessions: Dict[str, List[ChatMessage]] = defaultdict(list)
        self._lock = Lock()
        self._max_messages = max_messages

    def get_history(self, session_id: str) -> List[ChatMessage]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        message = ChatMessage(
            role=role,
            content=content,
        )

        with self._lock:
            self._sessions[session_id].append(message)

            if len(self._sessions[session_id]) > self._max_messages:
                self._sessions[session_id] = self._sessions[session_id][
                    -self._max_messages:
                ]

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


conversation_store = ConversationStore()
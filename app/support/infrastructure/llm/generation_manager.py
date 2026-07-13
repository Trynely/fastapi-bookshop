import asyncio
from typing import Dict

class LLMGenerationMGR:
    def __init__(self):
        self._tasks: Dict[int, asyncio.Task] = {}

    def add_task(self, chat_id: int, task: asyncio.Task):
        self.cancel_task(chat_id)
        self._tasks[chat_id] = task

    def remove_task(self, chat_id: int):
        self._tasks.pop(chat_id, None)

    def cancel_task(self, chat_id: int):
        task = self._tasks.get(chat_id)

        if task and not task.done():
            task.cancel()

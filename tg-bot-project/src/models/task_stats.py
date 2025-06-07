from datetime import datetime
from typing import Dict

class TaskStats:
    def __init__(self):
        self.views = 0
        self.clicks = 0
        self.starts = 0
        self.reactions = {}  # Dict[reaction_type: str, count: int]
        self.last_update = datetime.now()
        self.hourly_stats = {}  # Dict[hour: int, stats: Dict]
        self.errors = []
        self.success_rate = 100.0

    def update(self, views: int = 0, clicks: int = 0, starts: int = 0, reaction: str = None):
        self.views += views
        self.clicks += clicks
        self.starts += starts
        if reaction:
            self.reactions[reaction] = self.reactions.get(reaction, 0) + 1
        self.last_update = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "views": self.views,
            "clicks": self.clicks,
            "starts": self.starts,
            "reactions": self.reactions,
            "last_update": self.last_update.isoformat(),
            "success_rate": self.success_rate
        }

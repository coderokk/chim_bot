from typing import List, Tuple, Dict

class Paginator:
    def __init__(self, items: List, page_size: int = 30):
        self.items = items
        self.page_size = page_size
        self.total_pages = (len(items) + page_size - 1) // page_size

    def get_page(self, page: int) -> Tuple[List, bool, bool]:
        if page < 1:
            page = 1
        elif page > self.total_pages:
            page = self.total_pages

        start = (page - 1) * self.page_size
        end = start + self.page_size
        items = self.items[start:end]
        has_next = page < self.total_pages
        has_prev = page > 1
        
        return items, has_prev, has_next

    def get_page_info(self) -> Dict:
        return {
            "total_pages": self.total_pages,
            "items_per_page": self.page_size,
            "total_items": len(self.items)
        }

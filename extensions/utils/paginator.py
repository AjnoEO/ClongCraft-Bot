import miru
from typing import Callable

class PaginatorView(miru.View):
    def __init__(
            self, page: int, max_page: int, get_new_content_maxpage: Callable[[int], tuple[str, int]], 
            *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.page = page
        self.max_page = max_page
        self.get_new_content_maxpage = lambda: get_new_content_maxpage(self.page)
        self.update_items()

    def get_items(self) -> tuple[dict[str, miru.Button], miru.TextSelect]:
        ids = ["first_page", "prev_page", "next_page", "last_page"]
        return {id: self.get_item_by_id(id) for id in ids}, self.get_item_by_id("page_selector")

    def update_items(self):
        buttons, menu = self.get_items()
        buttons["first_page"].label = f"⏪ 1"
        buttons["prev_page"].label = f"⬅️ {self.page - 1 if self.page > 1 else '❌'}"
        buttons["next_page"].label = f"{self.page + 1 if self.page < self.max_page else '❌'} ➡️"
        buttons["last_page"].label = f"{self.max_page} ⏩"
        to_disable = []
        if self.page == 1: to_disable += ["first_page", "prev_page"]
        if self.page == self.max_page: to_disable += ["next_page", "last_page"]
        for button in buttons.values():
            button.disabled = button.custom_id in to_disable
        if self.page <= 12:
            from_page = 1
            to_page = min(25, self.max_page)
        elif self.max_page - self.page < 12:
            from_page = max(self.max_page - 24, 1)
            to_page = self.max_page
        else:
            from_page = self.page - 12
            to_page = self.page + 12
        menu.options = [
            miru.SelectOption(str(page), is_default=(page==self.page)) for page in range(from_page, to_page+1)
        ]

    async def update_message(self, ctx: miru.ViewContext):
        content, self.max_page = self.get_new_content_maxpage()
        self.update_items()
        await ctx.edit_response(content=content, components=self)

    @miru.button(label="<<", custom_id="first_page")
    async def first_page(self, ctx: miru.ViewContext, _) -> None:
        self.page = 1
        await self.update_message(ctx)

    @miru.button(label="<", custom_id="prev_page")
    async def prev_page(self, ctx: miru.ViewContext, _) -> None:
        self.page -= 1
        await self.update_message(ctx)

    @miru.button(label=">", custom_id="next_page")
    async def next_page(self, ctx: miru.ViewContext, _) -> None:
        self.page += 1
        await self.update_message(ctx)

    @miru.button(label="<", custom_id="last_page")
    async def last_page(self, ctx: miru.ViewContext, _) -> None:
        self.page = self.max_page
        await self.update_message(ctx)

    @miru.text_select(options=[], custom_id="page_selector")
    async def page_selector(self, ctx: miru.ViewContext, select: miru.TextSelect) -> None:
        self.page = int(select.values[0])
        await self.update_message(ctx)
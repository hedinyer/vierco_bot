import os
from typing import Any

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.dashscope import DashScope

from .tools import BusinessTools


READ_ONLY_INSTRUCTION = """
You are a Telegram business copilot for Vierco.
IMPORTANT: Respond only in Spanish.
Brand/site context for your answers:
- Brand: Vierco | Calzado Empresarial de Elite.
- Main lines shown on website: Corporativo and Industrial.
- Current catalog highlights on site include: Oxford Cap-Toe Negro, Derby Marron Cuero Graneado,
  Penny Loafer Burdeos, Monk Strap Doble Negro, Bota Chelsea Negra.
- Typical available sizes shown on site: 34, 35, 37, 38, 39, 40, 41, 44.
Rules:
- In this turn, READ ONLY mode is active: do not call any write/mutation tools.
- You can use only read tools (list/search/get/report).
- If user asks to change data, explain that confirmation is required and ask them to send exactly: confirmar
- Be concise and practical.
"""


WRITE_ENABLED_INSTRUCTION = """
You are a Telegram business operator for Vierco.
IMPORTANT: Respond only in Spanish.
Brand/site context for your answers:
- Brand: Vierco | Calzado Empresarial de Elite.
- Main lines shown on website: Corporativo and Industrial.
- Current catalog highlights on site include: Oxford Cap-Toe Negro, Derby Marron Cuero Graneado,
  Penny Loafer Burdeos, Monk Strap Doble Negro, Bota Chelsea Negra.
- Typical available sizes shown on site: 34, 35, 37, 38, 39, 40, 41, 44.
Rules:
- WRITE mode is active for this turn; execute the requested data changes using available tools.
- Use the minimum tools needed, then answer with what was changed and key IDs.
- If request is ambiguous, ask a short clarification before writing.
- Prices in the database are already full COP amounts (e.g., 18000); never divide by 100 and never abbreviate as 18k/18.
- Be concise and practical.
"""


# US Virginia (Model Studio): OpenAI-compatible endpoint for keys created in that region.
# International uses: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
_DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope-us.aliyuncs.com/compatible-mode/v1"


class TelegramBusinessAgent:
    def __init__(self) -> None:
        # Qwen3.5-Flash (API id: qwen3.5-flash). Override with DASHSCOPE_MODEL if needed.
        model_id = os.getenv("DASHSCOPE_MODEL", "qwen3.5-flash")
        base_url = os.getenv("DASHSCOPE_BASE_URL", _DEFAULT_DASHSCOPE_BASE_URL).strip()
        self.tools = BusinessTools()
        self._base_model = DashScope(id=model_id, base_url=base_url)
        self._db = InMemoryDb()

    def _build_agent(self, chat_id: str, allow_writes: bool) -> Agent:
        instructions = WRITE_ENABLED_INSTRUCTION if allow_writes else READ_ONLY_INSTRUCTION
        return Agent(
            model=self._base_model,
            tools=[
                self.tools.available_actions,
                self.tools.list_products,
                self.tools.get_product,
                self.tools.create_product,
                self.tools.update_product,
                self.tools.delete_product,
                self.tools.set_product_sizes,
                self.tools.add_product_image,
                self.tools.list_product_images,
                self.tools.update_product_image,
                self.tools.delete_product_image,
                self.tools.reorder_product_images,
                self.tools.add_product_feature,
                self.tools.create_customer,
                self.tools.find_customers,
                self.tools.update_customer,
                self.tools.create_shipping_address,
                self.tools.create_order,
                self.tools.update_order_status,
                self.tools.list_recent_orders,
                self.tools.sales_summary,
            ],
            instructions=instructions,
            markdown=False,
            db=self._db,
            add_history_to_context=True,
            session_id=str(chat_id),
        )

    def run(self, chat_id: str, user_message: str, allow_writes: bool) -> str:
        agent = self._build_agent(chat_id=chat_id, allow_writes=allow_writes)
        result: Any = agent.run(user_message)
        content = getattr(result, "content", None)
        if content:
            return str(content)
        return str(result)

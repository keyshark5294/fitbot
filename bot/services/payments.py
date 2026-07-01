"""YooKassa рекуррент + чек ФНС. Перенести логику из ConnectAssist.
Phase 0 — заглушки интерфейса."""
import logging

logger = logging.getLogger(__name__)


async def create_recurrent_payment(client_id: int, amount: str, plan: str) -> str:
    # TODO: перенос из ConnectAssist (создание платежа, сохранение payment_method_id)
    raise NotImplementedError


async def issue_fns_receipt(payment_id: str) -> None:
    # TODO: перенос из ConnectAssist (MoyNalog / ФНС чек)
    raise NotImplementedError

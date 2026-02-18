from datetime import timezone, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin.request_keyboards import get_request_actions_keyboard
from bot.lexicon.lexicon import type_names
from database.crud.admin_notifications import (
    create_admin_notification,
    deactivate_notifications_for_request,
    get_active_notifications_for_request,
)
from database.models import AbsenceRequest, Employee

MSK = timezone(timedelta(hours=3))


class NotificationService:
    """Сервис для отправки уведомлений."""

    def __init__(self, bot: Bot):
        """Инициализация сервиса."""

        self.bot = bot

    async def notify_admins_new_request(
        self,
        session: AsyncSession,
        request: AbsenceRequest,
        employee: Employee
    ) -> dict:
        """Уведомить всех админов о новой заявке."""

        admin_ids = await self._get_admin_telegram_ids(session)
        message_text = self._format_new_request(request, employee)
        keyboard = get_request_actions_keyboard(request.id)

        results = {"success": [], "failed": []}

        for admin_telegram_id in admin_ids:
            try:
                sent_message = await self.bot.send_message(
                    chat_id=admin_telegram_id,
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

                admin = await self._get_employee_by_telegram_id(
                    session, admin_telegram_id
                )

                if admin:
                    await create_admin_notification(
                        session,
                        request_id=request.id,
                        admin_id=admin.id,
                        message_id=sent_message.message_id,
                        chat_id=admin_telegram_id
                    )

                results["success"].append(admin_telegram_id)

            except Exception as e:
                results["failed"].append({
                    "id": admin_telegram_id,
                    "error": str(e)
                })

        await session.commit()
        return results

    async def update_admin_notifications(
        self,
        session: AsyncSession,
        request: AbsenceRequest,
        processed_by_admin_id: int,
        new_status: str,
        admin_name: str,
        reason: str | None = None
    ) -> None:
        """Обновить сообщения у других админов после обработки заявки."""

        notifications = await get_active_notifications_for_request(
            session,
            request.id,
            exclude_admin_id=processed_by_admin_id
        )

        if new_status == "approved":
            status_text = "✅ ОДОБРЕНО"
        else:
            status_text = "❌ ОТКЛОНЕНО"

        for notification in notifications:
            try:
                original_text = self._format_new_request(
                    request,
                    request.employee
                )

                updated_text = (
                    f"{original_text}\n\n"
                    f"{'─' * 20}\n"
                    f"{status_text}\n"
                    f"👤 Обработал: {admin_name}"
                )

                if reason:
                    updated_text += f"\n💬 Причина: {reason}"

                await self.bot.edit_message_text(
                    chat_id=notification.chat_id,
                    message_id=notification.message_id,
                    text=updated_text,
                    reply_markup=None,
                    parse_mode="HTML"
                )

            except TelegramBadRequest:
                pass

        await deactivate_notifications_for_request(
            session,
            request.id,
            exclude_admin_id=processed_by_admin_id
        )

    async def notify_admins_request_cancelled(
        self,
        session: AsyncSession,
        request: AbsenceRequest,
        employee: Employee
    ) -> None:
        """Уведомить админов об отмене заявки пользователем."""

        notifications = await get_active_notifications_for_request(
            session,
            request.id
        )

        full_name = f"{employee.last_name} {employee.name}"

        for notification in notifications:
            try:
                original_text = self._format_new_request(request, employee)

                updated_text = (
                    f"{original_text}\n\n"
                    f"{'─' * 20}\n"
                    f"🚫 ОТМЕНЕНО СОТРУДНИКОМ\n"
                    f"👤 Отменил: {full_name}"
                )

                await self.bot.edit_message_text(
                    chat_id=notification.chat_id,
                    message_id=notification.message_id,
                    text=updated_text,
                    reply_markup=None,
                    parse_mode="HTML"
                )

            except TelegramBadRequest:
                pass

        await deactivate_notifications_for_request(session, request.id)

    async def notify_user_request_created(
        self,
        telegram_id: int,
        request: AbsenceRequest
    ) -> bool:
        """Уведомить пользователя о создании заявки."""

        days = (request.end_date - request.start_date).days + 1
        type_name = type_names.get(request.request_type, request.request_type)

        text = (
            "✅ <b>Заявка успешно отправлена!</b>\n\n"
            f"🆔 Номер: <b>#{request.id}</b>\n"
            f"📋 Тип: {type_name}\n"
            f"📅 Период: {request.start_date.strftime('%d.%m.%Y')} — "
            f"{request.end_date.strftime('%d.%m.%Y')} ({days} дн.)\n"
        )

        if request.comment:
            text += f"💬 Комментарий: {request.comment}\n"

        text += "\n⏳ <i>Ожидайте решения администратора.</i>"

        return await self._safe_send(telegram_id, text)

    async def notify_user_request_approved(
        self,
        telegram_id: int,
        request: AbsenceRequest,
        admin_name: str | None = None
    ) -> bool:
        """Уведомить пользователя об одобрении заявки."""

        type_name = type_names.get(request.request_type, request.request_type)

        text = (
            "✅ <b>Ваша заявка одобрена!</b>\n\n"
            f"🆔 Номер: #{request.id}\n"
            f"📋 Тип: {type_name}\n"
            f"📅 Период: {request.start_date.strftime('%d.%m.%Y')} — "
            f"{request.end_date.strftime('%d.%m.%Y')}\n"
        )

        if admin_name:
            text += f"👤 Одобрил: {admin_name}\n"

        text += "\n🎉 <i>Хорошего отдыха!</i>"

        return await self._safe_send(telegram_id, text)

    async def notify_user_request_rejected(
        self,
        telegram_id: int,
        request: AbsenceRequest,
        reason: str | None = None,
        admin_name: str | None = None
    ) -> bool:
        """Уведомить пользователя об отклонении заявки."""

        type_name = type_names.get(request.request_type, request.request_type)

        text = (
            "❌ <b>Ваша заявка отклонена</b>\n\n"
            f"🆔 Номер: #{request.id}\n"
            f"📋 Тип: {type_name}\n"
            f"📅 Период: {request.start_date.strftime('%d.%m.%Y')} — "
            f"{request.end_date.strftime('%d.%m.%Y')}\n"
        )

        if admin_name:
            text += f"👤 Отклонил: {admin_name}\n"

        if reason:
            text += f"\n💬 <b>Причина:</b> {reason}\n"

        text += "\n<i>Обратитесь к администратору для уточнения.</i>"

        return await self._safe_send(telegram_id, text)

    async def _safe_send(self, chat_id: int, text: str) -> bool:
        """Безопасная отправка сообщения."""

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            return True
        except Exception:
            return False

    async def _get_admin_telegram_ids(
        self,
        session: AsyncSession
    ) -> list[int]:
        """Получить telegram_id всех активных админов."""

        result = await session.execute(
            select(Employee.telegram_id).where(
                Employee.role.in_(["admin", "superuser"]),
                Employee.telegram_id.isnot(None),
                Employee.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def _get_employee_by_telegram_id(
        self,
        session: AsyncSession,
        telegram_id: int
    ) -> Employee | None:
        """Получить сотрудника по telegram_id."""

        result = await session.execute(
            select(Employee).where(Employee.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    def _format_new_request(
        self,
        request: AbsenceRequest,
        employee: Employee
    ) -> str:
        """Форматировать сообщение о новой заявке."""

        days = (request.end_date - request.start_date).days + 1
        type_name = type_names.get(request.request_type, request.request_type)
        created_at_msk = request.created_at.replace(
            tzinfo=timezone.utc
        ).astimezone(MSK)
        full_name = f"{employee.last_name} {employee.name}"
        if employee.patronymic:
            full_name += f" {employee.patronymic}"

        text = (
            "📋 <b>Новая заявка на отсутствие</b>\n\n"
            f"👤 <b>Сотрудник:</b> {full_name}\n"
            f"📧 <b>Email:</b> {employee.email}\n"
            f"💼 <b>Должность:</b> {employee.position or 'не указана'}\n\n"
            f"📌 <b>Тип:</b> {type_name}\n"
            f"📅 <b>Период:</b> {request.start_date.strftime('%d.%m.%Y')} — "
            f"{request.end_date.strftime('%d.%m.%Y')} ({days} дн.)\n"
        )

        if request.comment:
            text += f"💬 <b>Комментарий:</b> {request.comment}\n"

        text += (
            f"\n🕐 <b>Подано:</b> "
            f"{created_at_msk.strftime('%d.%m.%Y %H:%M')} (МСК)\n"
            f"🆔 <b>ID:</b> #{request.id}"
        )

        return text

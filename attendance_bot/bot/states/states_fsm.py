"""Состояния FSM для всех процессов бота."""

from aiogram.fsm.state import State, StatesGroup


class RegisterStates(StatesGroup):
    """Состояния для регистрации пользователя."""

    waiting_email = State()
    waiting_code = State()


class AddEmployeeStates(StatesGroup):
    """Состояния для добавления сотрудника."""

    waiting_name = State()
    waiting_last_name = State()
    waiting_email = State()
    waiting_position = State()
    waiting_role = State()


class InviteCodeStates(StatesGroup):
    """Состояния для создания инвайт-кода."""

    waiting_email = State()


class DeactivateStates(StatesGroup):
    """Состояния для деактивации сотрудника."""

    waiting_email = State()


class DeleteStates(StatesGroup):
    """Состояния для удаления сотрудника."""

    waiting_email = State()
    confirming = State()


class CreateRequestStates(StatesGroup):
    """Состояния для создания заявки на отсутствие."""

    choosing_type = State()
    entering_start_date = State()
    entering_end_date = State()
    entering_comment = State()
    confirming = State()

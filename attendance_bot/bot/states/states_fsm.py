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
    confirming = State()


class InviteCodeStates(StatesGroup):
    """Состояния для создания инвайт-кода."""

    waiting_email = State()


class DeleteStates(StatesGroup):
    """Состояния для удаления сотрудника."""

    waiting_email = State()
    confirming = State()


class CreateRequestStates(StatesGroup):
    """Состояния создания заявки."""

    choosing_type = State()
    entering_start_date = State()
    entering_end_date = State()
    entering_partial_date = State()
    entering_partial_start_time = State()
    entering_partial_end_time = State()
    entering_comment = State()
    confirming = State()

    keyboard_type = State()
    keyboard_message_id = State()


class RejectRequestStates(StatesGroup):
    """Состояния для отклонения заявки."""

    entering_reason = State()

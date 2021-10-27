class UnregisteredUserError(Exception):
    def __init__(self, user):
        super().__init__(f'Could not query for unregistered user - {user}')


class UserMismatchError(Exception):
    def __init__(self, user_data, user):
        super().__init__(f'User data {user_data} does not belong to user {user}.')


class UserUpdateError(Exception):
    def __init__(self, user):
        super().__init__(f'Cannot update user {user}. User is not registered.')


class InvalidGlobalOperation(Exception):
    def __init__(self, user_context_manager, operation):
        super().__init__(f'{user_context_manager} - Operation: `{operation}` cannot be called from a global context. Must be called from a User context')


class InvalidEmail(Exception):
    def __init__(self, user: str, email: str):
        super().__init__(f'{email} from {user} - Invalid Pennstate email format.')
        self.email = email


class ConfirmationEmailMismatch(Exception):
    def __init__(self, user: str, email: str, confirmation: str):
        super().__init__(f'{email} and {confirmation} do not match for user {user}.')
        self.email = email
        self.confirmation = confirmation

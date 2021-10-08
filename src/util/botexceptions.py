class UnregisteredUserError(Exception):
    def __init__(self, user):
        super().__init__(f'Could not query for unregistered user - {user}')


class UserMismatchError(Exception):
    def __init__(self, user_data, user):
        super().__init__(f'User data {user_data} does not belong to user {user}.')


class InvalidGlobalOperation(Exception):
    def __init__(self, user_context_manager, operation):
        super().__init__(f'{user_context_manager} - Operation: `{operation}` cannot be called from a global context. Must be called from a User context')

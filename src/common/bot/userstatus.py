from collections import Callable

from common import OrderedEnum


class UserStatus(OrderedEnum):
    # Order of status matters.
    PENDING_BOTH = (1, '\U00002709 \U0001F4CE Awaiting Email & Canvas Image')       # waiting for the user to respond to DMs and email
    PENDING_DM = (2, '\U0001F4CE Awaiting Canvas Image')                            # waiting for the user to respond to DMs
    PENDING_EMAIL = (3, '\U00002709 Awaiting Email')                                # waiting for the user to respond to email
    AWAITING_VERIFICATION = (4, '\U0001F510 Awaiting Verification')                 # waiting admin to verify user
    VERIFIED = (5, '\U00002714 Verified')                                           # user has been verified by admin
    DENIED = (6, '\U0000274C Rejected')                                             # user was denied from the verification process.
    ATTEMPTED = (7, '\U000026A0 Attempted')                                         # an issue was encountered during the verification process. updates to user information required.
    TERMINATED = (8, ' Email response timeout. This user is required to restart the verification process')                  # user did not respond to the email in the allotted amount of days.

    def __init__(self, int_val: int, representation: str):
        self._value_ = int_val
        self.representation: str = representation

    def __repr__(self):
        return self.representation


ComparableStatus = Callable[[UserStatus], bool]
StatusContext = Callable[[UserStatus], UserStatus]


def canvas_image_received(status: UserStatus) -> UserStatus:
    if status == UserStatus.PENDING_BOTH:
        return UserStatus.PENDING_EMAIL
    return UserStatus.AWAITING_VERIFICATION


def canvas_image_requested(status: UserStatus) -> UserStatus:
    if status == UserStatus.PENDING_EMAIL:
        return UserStatus.PENDING_BOTH
    return UserStatus.PENDING_DM


def email_received(status: UserStatus) -> UserStatus:
    if status == UserStatus.PENDING_BOTH:
        return UserStatus.PENDING_DM
    return UserStatus.AWAITING_VERIFICATION


def user_verified(_: UserStatus) -> UserStatus:
    return UserStatus.VERIFIED


def user_denied(_: UserStatus) -> UserStatus:
    return UserStatus.DENIED


def user_terminated(_: UserStatus) -> UserStatus:
    return UserStatus.TERMINATED


def stall_verification(_: UserStatus) -> UserStatus:
    return UserStatus.ATTEMPTED


def is_user_pending_email(status: UserStatus) -> bool:
    return status == UserStatus.PENDING_BOTH or status == UserStatus.PENDING_EMAIL


def is_user_pending_dm(status: UserStatus) -> bool:
    return status < UserStatus.PENDING_EMAIL

from dataclasses import dataclass, field, astuple


@dataclass
class UserDetails:
    user_id: int
    joined_timestamp: float
    first_name: str
    last_name: str
    psu_email: str
    status_msg_id: int
    dm_channel_id: int
    status: str
    image_urls: list[str] = field(default_factory=list)

    def to_row(self) -> tuple[int, float, str, str, str, int, int, str]:
        return astuple(self)[:-1]

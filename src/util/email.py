from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email as eml

import smtplib as smtp
import imaplib as imap
from enum import IntEnum

from extensions.userdata import UserData
from main import google_cfg


class EmailStatus(IntEnum):
    UNDELIVERED = 1
    VALID_REPLY = 2
    TIMEOUT = 3


class Gmail:
    content: str = 'Please respond to this email to verify your discord identity.\n\n' \
                   '(This is an automated email. Please ignore this email if you did not request verification)'
    email_subject: str = 'PSU Software Discord Verification Email'

    def __init__(self):
        self.__smtp_conn: smtp.SMTP = self.__new_smtp_conn
        self.__imap_conn: imap.IMAP4_SSL = self.__new_imap_conn

    @property
    def __new_smtp_conn(self):
        conn = smtp.SMTP('smtp.gmail.com', 587)
        conn.ehlo()
        conn.starttls()
        conn.ehlo()
        conn.login(google_cfg.email, google_cfg.password)
        return conn

    @property
    def __new_imap_conn(self):
        conn = imap.IMAP4_SSL('imap.gmail.com')
        conn.login(google_cfg.email, google_cfg.password)
        conn.select('"[Gmail]/All Mail"')
        return conn

    @property
    def __smtp(self) -> smtp.SMTP:
        """
        Proxy for __smtp_conn. This property should be used over __smtp_conn since this property handles disconnect
        logic.
        """
        try:
            status, _ = self.__smtp_conn.noop()
        except smtp.SMTPServerDisconnected:
            self.__smtp_conn.quit()
            self.__smtp_conn = self.__new_smtp_conn
        return self.__smtp_conn

    def send_email_to(self, email: str):
        message = MIMEMultipart()
        message['From'] = google_cfg.email
        message['To'] = email
        message['Subject'] = Gmail.email_subject + f' - {email}'
        message.attach(MIMEText(Gmail.content, 'plain'))
        self.__smtp.send_message(message)

    def check_for_replies(self, users_pending_emails: list[UserData]) -> list[tuple[UserData, EmailStatus]]:
        users_with_replies: list[tuple[UserData, EmailStatus]] = []
        self.__imap_conn.noop()
        for user in users_pending_emails:
            _, responses = self.__imap_conn.uid('SEARCH', f'(SUBJECT "{Gmail.email_subject} - {user.psu_email}" UNSEEN)')
            responses = responses[0].split()
            if len(responses) == 0:
                # if datetime.now() - user.joined > 14 days: tag as timeout
                continue
            _, msg_data = self.__imap_conn.uid('FETCH', responses[0], '(BODY[HEADER])')
            msg = eml.message_from_bytes(msg_data[0][1])
            if msg['From'] in 'postmaster@pennstateoffice365.onmicrosoft.com':
                users_with_replies.append((user, EmailStatus.UNDELIVERED))
                continue
            users_with_replies.append((user, EmailStatus.VALID_REPLY))
        return users_with_replies

    def unload(self):
        self.__smtp_conn.quit()
        self.__imap_conn.logout()

import email
import imaplib
from typing import Iterator

from .base import RawDocument, Source


class EmailSource(Source):
    def __init__(self, host: str, user: str, password: str, folder: str = "INBOX"):
        self.host = host
        self.user = user
        self.password = password
        self.folder = folder

    def fetch_new(self) -> Iterator[RawDocument]:
        with imaplib.IMAP4_SSL(self.host) as conn:
            conn.login(self.user, self.password)
            conn.select(self.folder)
            status, data = conn.search(None, "UNSEEN")
            if status != "OK":
                return
            for message_id in data[0].split():
                status, msg_data = conn.fetch(message_id, "(RFC822)")
                if status != "OK":
                    continue
                message = email.message_from_bytes(msg_data[0][1])
                yield from self._pdf_attachments(message)

    def _pdf_attachments(self, message: email.message.Message) -> Iterator[RawDocument]:
        for part in message.walk():
            filename = part.get_filename()
            if not filename or not filename.lower().endswith(".pdf"):
                continue
            payload = part.get_payload(decode=True)
            if payload:
                yield RawDocument(filename=filename, content=payload, origin=f"email:{message.get('From', '')}")

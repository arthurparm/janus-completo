from unittest.mock import MagicMock

from app.services.chat_service import ChatService


def test_chat_service_injects_event_logger_into_event_publisher():
    repo = MagicMock()
    llm_service = MagicMock()
    event_logger = MagicMock()

    service = ChatService(repo=repo, llm_service=llm_service, event_logger=event_logger)

    assert service._event_publisher.db_logger is event_logger


def test_chat_service_keeps_db_logger_none_when_not_provided():
    repo = MagicMock()
    llm_service = MagicMock()

    service = ChatService(repo=repo, llm_service=llm_service)

    assert service._event_publisher.db_logger is None

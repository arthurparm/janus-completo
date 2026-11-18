from __future__ import annotations

from app.models.ab_experiment_models import Experiment, ExperimentArm, ExperimentResult
from app.models.user_models import User
from app.repositories.ab_experiment_repository import ABExperimentRepository
from app.repositories.feedback_repository import (
    FeedbackRepository,
    OwnedConversationNotFoundError,
)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def test_evaluation_queries_are_owner_scoped_and_reject_cross_experiment_arms(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'evaluation.db'}")
    User.__table__.create(engine)
    Experiment.__table__.create(engine)
    ExperimentArm.__table__.create(engine)
    ExperimentResult.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    try:
        repo = ABExperimentRepository(session)
        owned = repo.create_experiment("owned", owner_user_id=1)
        foreign = repo.create_experiment("foreign", owner_user_id=2)
        owned_arm = repo.add_arm(owned.id, 1, "owned-arm", "model-a")
        foreign_arm = repo.add_arm(foreign.id, 2, "foreign-arm", "model-b")

        assert owned_arm is not None
        assert foreign_arm is not None
        assert repo.get_owned_experiment(owned.id, 2) is None
        assert repo.add_arm(owned.id, 2, "blocked", "model-x") is None
        assert repo.add_result(
            owned.id,
            foreign_arm.id,
            "accuracy",
            1.0,
            owner_user_id=1,
        ) is None
        assert [item.id for item in repo.list_experiments(1)] == [owned.id]
    finally:
        session.close()


def test_feedback_creation_and_reads_are_owner_scoped(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'feedback.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE feedback_entries (
                    id VARCHAR(36) PRIMARY KEY,
                    owner_user_id INTEGER NOT NULL,
                    conversation_id VARCHAR(100) NOT NULL,
                    message_id VARCHAR(100),
                    rating VARCHAR(20) NOT NULL,
                    feedback_type VARCHAR(20) NOT NULL,
                    comment TEXT,
                    context_json JSON,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

    class OwnedChatRepository:
        def __init__(self, *args, **kwargs):
            pass

        def get_conversation(self, conversation_id):
            if conversation_id != "conversation-a":
                raise LookupError
            return {"user_id": "1", "messages": [{"id": "message-a"}]}

    monkeypatch.setattr(
        "app.repositories.feedback_repository.ChatRepositorySQL",
        OwnedChatRepository,
    )
    session = sessionmaker(bind=engine)()
    try:
        repo = FeedbackRepository(session)
        created = repo.create(
            feedback_id="feedback-a",
            owner_user_id=1,
            conversation_id="conversation-a",
            message_id="message-a",
            rating="positive",
            feedback_type="message",
            comment=None,
            context={},
        )
        assert created.owner_user_id == 1
        assert [item.id for item in repo.list_for_owner(owner_user_id=1)] == ["feedback-a"]
        assert repo.list_for_owner(owner_user_id=2) == []

        for owner, message in ((2, "message-a"), (1, "message-b")):
            try:
                repo.assert_owned_conversation(
                    owner_user_id=owner,
                    conversation_id="conversation-a",
                    message_id=message,
                )
            except OwnedConversationNotFoundError:
                pass
            else:
                raise AssertionError("cross-owner feedback access was accepted")
    finally:
        session.close()

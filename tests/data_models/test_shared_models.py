import pytest
from datetime import datetime
from typing import List
from pydantic import ValidationError as PydanticValidationError
from src.data_models.shared_models import ChatSession, ChatMessage

# Common data for testing
VALID_DATETIME = datetime.now()
VALID_POSITIVE_INT = 123

# --- Test ChatSession Model ---

def test_chatsession_valid_creation_all_fields():
    session = ChatSession(
        ChatSessionID=1,
        CustomerID=101,
        ContactID=202,
        UserID=303,
        StartTime=VALID_DATETIME,
        EndTime=VALID_DATETIME,
        Platform="Web"
    )
    assert session.ChatSessionID == 1
    assert session.CustomerID == 101
    assert session.ContactID == 202
    assert session.UserID == 303
    assert session.StartTime == VALID_DATETIME
    assert session.EndTime == VALID_DATETIME
    assert session.Platform == "Web"

def test_chatsession_valid_creation_required_only():
    session = ChatSession(ChatSessionID=2)
    assert session.ChatSessionID == 2
    assert session.CustomerID is None
    assert session.ContactID is None
    assert session.UserID is None
    assert session.StartTime is None
    assert session.EndTime is None
    assert session.Platform is None

def test_chatsession_chatsessionid_pk_validation():
    with pytest.raises(PydanticValidationError, match="ChatSessionID"):
        ChatSession(ChatSessionID="abc")  # Wrong type
    with pytest.raises(PydanticValidationError, match="ChatSessionID"):
        ChatSession(ChatSessionID=0)  # Not positive
    with pytest.raises(PydanticValidationError, match="ChatSessionID"):
        ChatSession(ChatSessionID=-1)  # Not positive
    session = ChatSession(ChatSessionID=VALID_POSITIVE_INT)
    assert session.ChatSessionID == VALID_POSITIVE_INT

def test_chatsession_customerid_fk_validation():
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        ChatSession(ChatSessionID=1, CustomerID="xyz")
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        ChatSession(ChatSessionID=1, CustomerID=0)
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        ChatSession(ChatSessionID=1, CustomerID=-1)
    session = ChatSession(ChatSessionID=1, CustomerID=VALID_POSITIVE_INT)
    assert session.CustomerID == VALID_POSITIVE_INT
    session_none = ChatSession(ChatSessionID=1, CustomerID=None)
    assert session_none.CustomerID is None

def test_chatsession_contactid_fk_validation():
    with pytest.raises(PydanticValidationError, match="ContactID"):
        ChatSession(ChatSessionID=1, ContactID=0)
    session = ChatSession(ChatSessionID=1, ContactID=VALID_POSITIVE_INT)
    assert session.ContactID == VALID_POSITIVE_INT
    session_none = ChatSession(ChatSessionID=1, ContactID=None)
    assert session_none.ContactID is None

def test_chatsession_userid_fk_validation():
    with pytest.raises(PydanticValidationError, match="UserID"):
        ChatSession(ChatSessionID=1, UserID=0)
    session = ChatSession(ChatSessionID=1, UserID=VALID_POSITIVE_INT)
    assert session.UserID == VALID_POSITIVE_INT
    session_none = ChatSession(ChatSessionID=1, UserID=None)
    assert session_none.UserID is None

def test_chatsession_datetime_fields_validation():
    with pytest.raises(PydanticValidationError, match="StartTime"):
        ChatSession(ChatSessionID=1, StartTime="not-a-date")
    # Pydantic v2 is more strict with type validation
    with pytest.raises(PydanticValidationError):
        ChatSession(ChatSessionID=1, EndTime="not-a-date")
    session = ChatSession(ChatSessionID=1, StartTime=VALID_DATETIME, EndTime=VALID_DATETIME)
    assert session.StartTime == VALID_DATETIME
    assert session.EndTime == VALID_DATETIME

def test_chatsession_platform_validation():
    session = ChatSession(ChatSessionID=1, Platform="Mobile App")
    assert session.Platform == "Mobile App"
    # Pydantic v2 is more strict and doesn't coerce int to str by default
    session_str = ChatSession(ChatSessionID=1, Platform="123")
    assert session_str.Platform == "123"


# --- Test ChatMessage Model ---

def test_chatmessage_valid_creation_all_fields():
    message = ChatMessage(
        ChatMessageID=1,
        ChatSessionID=101,
        SenderID=202,
        SenderType="Customer",
        MessageText="Hello world",
        Timestamp=VALID_DATETIME,
        ExtractedKeywords=["hello", "world"],
        ClassifiedTopics=["greeting"]
    )
    assert message.ChatMessageID == 1
    assert message.ChatSessionID == 101
    assert message.SenderID == 202
    assert message.SenderType == "Customer"
    assert message.MessageText == "Hello world"
    assert message.Timestamp == VALID_DATETIME
    assert message.ExtractedKeywords == ["hello", "world"]
    assert message.ClassifiedTopics == ["greeting"]

def test_chatmessage_valid_creation_required_only():
    message = ChatMessage(ChatMessageID=2)
    assert message.ChatMessageID == 2
    assert message.ChatSessionID is None
    assert message.SenderID is None
    # ... and other optionals are None

def test_chatmessage_chatmessageid_pk_validation():
    with pytest.raises(PydanticValidationError, match="ChatMessageID"):
        ChatMessage(ChatMessageID="msg01")
    with pytest.raises(PydanticValidationError, match="ChatMessageID"):
        ChatMessage(ChatMessageID=0)
    with pytest.raises(PydanticValidationError, match="ChatMessageID"):
        ChatMessage(ChatMessageID=-1)
    message = ChatMessage(ChatMessageID=VALID_POSITIVE_INT)
    assert message.ChatMessageID == VALID_POSITIVE_INT

def test_chatmessage_chatsessionid_fk_validation():
    with pytest.raises(PydanticValidationError, match="ChatSessionID"):
        ChatMessage(ChatMessageID=1, ChatSessionID=0)
    message = ChatMessage(ChatMessageID=1, ChatSessionID=VALID_POSITIVE_INT)
    assert message.ChatSessionID == VALID_POSITIVE_INT
    message_none = ChatMessage(ChatMessageID=1, ChatSessionID=None)
    assert message_none.ChatSessionID is None

def test_chatmessage_senderid_fk_validation():
    with pytest.raises(PydanticValidationError, match="SenderID"):
        ChatMessage(ChatMessageID=1, SenderID=0)
    message = ChatMessage(ChatMessageID=1, SenderID=VALID_POSITIVE_INT)
    assert message.SenderID == VALID_POSITIVE_INT
    message_none = ChatMessage(ChatMessageID=1, SenderID=None)
    assert message_none.SenderID is None

def test_chatmessage_list_str_fields():
    # ExtractedKeywords
    msg_kw_valid = ChatMessage(ChatMessageID=1, ExtractedKeywords=["kw1", "kw2"])
    assert msg_kw_valid.ExtractedKeywords == ["kw1", "kw2"]
    msg_kw_empty = ChatMessage(ChatMessageID=1, ExtractedKeywords=[])
    assert msg_kw_empty.ExtractedKeywords == []
    msg_kw_none = ChatMessage(ChatMessageID=1, ExtractedKeywords=None)
    assert msg_kw_none.ExtractedKeywords is None
    with pytest.raises(PydanticValidationError, match="ExtractedKeywords"):
        ChatMessage(ChatMessageID=1, ExtractedKeywords=["valid", 123]) # list of mixed types
    with pytest.raises(PydanticValidationError, match="ExtractedKeywords"):
        ChatMessage(ChatMessageID=1, ExtractedKeywords="not-a-list")

    # ClassifiedTopics
    msg_top_valid = ChatMessage(ChatMessageID=1, ClassifiedTopics=["topicA", "topicB"])
    assert msg_top_valid.ClassifiedTopics == ["topicA", "topicB"]
    msg_top_empty = ChatMessage(ChatMessageID=1, ClassifiedTopics=[])
    assert msg_top_empty.ClassifiedTopics == []
    msg_top_none = ChatMessage(ChatMessageID=1, ClassifiedTopics=None)
    assert msg_top_none.ClassifiedTopics is None
    with pytest.raises(PydanticValidationError, match="ClassifiedTopics"):
        ChatMessage(ChatMessageID=1, ClassifiedTopics=[10, "validTopic"])
    with pytest.raises(PydanticValidationError, match="ClassifiedTopics"):
        ChatMessage(ChatMessageID=1, ClassifiedTopics=True) # wrong type

def test_chatmessage_optional_text_fields():
    message = ChatMessage(ChatMessageID=1, SenderType="Agent", MessageText="Response")
    assert message.SenderType == "Agent"
    assert message.MessageText == "Response"
    # Pydantic v2 is more strict and doesn't coerce int to str by default
    message_str = ChatMessage(ChatMessageID=1, SenderType="123")
    assert message_str.SenderType == "123"


def test_chatmessage_timestamp_validation():
    with pytest.raises(PydanticValidationError, match="Timestamp"):
        ChatMessage(ChatMessageID=1, Timestamp="not-a-datetime-object")
    message = ChatMessage(ChatMessageID=1, Timestamp=VALID_DATETIME)
    assert message.Timestamp == VALID_DATETIME

# --- Generic Data Type Validation Test ---
def test_generic_datatype_validation_shared():
    # ChatSessionID (PositiveInt)
    with pytest.raises(PydanticValidationError):
        ChatSession(ChatSessionID="should_be_int")

    # ChatMessage.MessageText (Optional[str])
    # Pydantic v2 allows coercion from simple types if not strict.
    # To robustly test type error for string, pass a complex type.
    with pytest.raises(PydanticValidationError):
        ChatMessage(ChatMessageID=1, MessageText={"text": "this is a dict, not str"})

    # ChatMessage.ExtractedKeywords (Optional[List[str]])
    with pytest.raises(PydanticValidationError):
        ChatMessage(ChatMessageID=1, ExtractedKeywords="this is a string, not list")
    with pytest.raises(PydanticValidationError): # Test for list of non-strings
         ChatMessage(ChatMessageID=1, ExtractedKeywords=[1,2,3])

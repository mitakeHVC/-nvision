from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, PositiveInt, Field

class ChatSession(BaseModel):
    ChatSessionID: PositiveInt = Field(..., alias='ChatSessionID')
    CustomerID: Optional[PositiveInt] = Field(None, alias='CustomerID')
    ContactID: Optional[PositiveInt] = Field(None, alias='ContactID')
    UserID: Optional[PositiveInt] = Field(None, alias='UserID') # CRM User/Support Agent
    StartTime: Optional[datetime] = Field(None, alias='StartTime')
    EndTime: Optional[datetime] = Field(None, alias='EndTime')
    Platform: Optional[str] = Field(None, alias='Platform') # e.g., Web, Mobile App

    class Config:
        allow_population_by_field_name = True

class ChatMessage(BaseModel):
    ChatMessageID: PositiveInt = Field(..., alias='ChatMessageID')
    ChatSessionID: Optional[PositiveInt] = Field(None, alias='ChatSessionID')
    SenderID: Optional[PositiveInt] = Field(None, alias='SenderID') # Could be CustomerID or UserID
    SenderType: Optional[str] = Field(None, alias='SenderType') # e.g., 'Customer', 'Agent'
    MessageText: Optional[str] = Field(None, alias='MessageText')
    Timestamp: Optional[datetime] = Field(None, alias='Timestamp')
    ExtractedKeywords: Optional[List[str]] = Field(None, alias='ExtractedKeywords')
    ClassifiedTopics: Optional[List[str]] = Field(None, alias='ClassifiedTopics')

    class Config:
        allow_population_by_field_name = True

# Example Usage (optional, for testing):
# if __name__ == "__main__":
#     session_data = {
#         "ChatSessionID": 1001,
#         "CustomerID": 1,
#         "UserID": 50,
#         "StartTime": datetime.now(),
#         "Platform": "Web"
#     }
#     chat_session = ChatSession(**session_data)
#     print("ChatSession:")
#     print(chat_session.json(indent=2, by_alias=True))

#     message_data = {
#         "ChatMessageID": 2001,
#         "ChatSessionID": 1001,
#         "SenderID": 1,
#         "SenderType": "Customer",
#         "MessageText": "Hello, I need help with my order.",
#         "Timestamp": datetime.now(),
#         "ExtractedKeywords": ["help", "order"]
#     }
#     chat_message = ChatMessage(**message_data)
#     print("\nChatMessage:")
#     print(chat_message.json(indent=2, by_alias=True))

#     # Example with missing non-required field
#     session_data_minimal = {
#         "ChatSessionID": 1002,
#     }
#     chat_session_minimal = ChatSession(**session_data_minimal)
#     print("\nChatSession (Minimal):")
#     print(chat_session_minimal.json(indent=2, by_alias=True))

#     # Example showing error for missing required PK
#     try:
#         invalid_session_data = {
#             "CustomerID": 1
#         }
#         chat_session_invalid = ChatSession(**invalid_session_data)
#     except ValueError as e:
#         print(f"\nError for invalid session data: {e}")

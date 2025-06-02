from typing import Optional
from datetime import datetime
from pydantic import BaseModel, PositiveInt, NonNegativeFloat, NonNegativeInt, EmailStr, Field, ConfigDict

class Contact(BaseModel):
    ContactID: PositiveInt = Field(..., alias='ContactID')
    FirstName: Optional[str] = Field(None, alias='FirstName')
    LastName: Optional[str] = Field(None, alias='LastName')
    Email: Optional[EmailStr] = Field(None, alias='Email')
    PhoneNumber: Optional[str] = Field(None, alias='PhoneNumber')
    JobTitle: Optional[str] = Field(None, alias='JobTitle')
    CompanyID: Optional[PositiveInt] = Field(None, alias='CompanyID') # Foreign Key
    LeadSource: Optional[str] = Field(None, alias='LeadSource')
    DateCreated: Optional[datetime] = Field(None, alias='DateCreated')
    LastContactedDate: Optional[datetime] = Field(None, alias='LastContactedDate')

    model_config = ConfigDict(populate_by_name=True)

class Company(BaseModel):
    CompanyID: PositiveInt = Field(..., alias='CompanyID')
    CompanyName: Optional[str] = Field(None, alias='CompanyName')
    Industry: Optional[str] = Field(None, alias='Industry')
    Website: Optional[str] = Field(None, alias='Website') # Should ideally be HttpUrl
    Address: Optional[str] = Field(None, alias='Address')
    PhoneNumber: Optional[str] = Field(None, alias='PhoneNumber')
    AnnualRevenue: Optional[NonNegativeFloat] = Field(None, alias='AnnualRevenue')
    NumberOfEmployees: Optional[NonNegativeInt] = Field(None, alias='NumberOfEmployees')

    model_config = ConfigDict(populate_by_name=True)

class Interaction(BaseModel):
    InteractionID: PositiveInt = Field(..., alias='InteractionID')
    ContactID: Optional[PositiveInt] = Field(None, alias='ContactID') # Foreign Key
    CompanyID: Optional[PositiveInt] = Field(None, alias='CompanyID') # Foreign Key, optional
    InteractionType: Optional[str] = Field(None, alias='InteractionType') # E.g., Email, Call, Meeting, Note
    InteractionDate: Optional[datetime] = Field(None, alias='InteractionDate')
    Subject: Optional[str] = Field(None, alias='Subject')
    Notes: Optional[str] = Field(None, alias='Notes') # Text content of the interaction
    AssignedToUserID: Optional[PositiveInt] = Field(None, alias='AssignedToUserID') # CRM User, Foreign Key

    model_config = ConfigDict(populate_by_name=True)

class Deal(BaseModel):
    DealID: PositiveInt = Field(..., alias='DealID')
    DealName: Optional[str] = Field(None, alias='DealName')
    CompanyID: Optional[PositiveInt] = Field(None, alias='CompanyID') # Foreign Key
    PrimaryContactID: Optional[PositiveInt] = Field(None, alias='PrimaryContactID') # Foreign Key
    Stage: Optional[str] = Field(None, alias='Stage') # E.g., Qualification, Proposal, Negotiation, Closed Won, Closed Lost
    Amount: Optional[NonNegativeFloat] = Field(None, alias='Amount')
    ExpectedCloseDate: Optional[datetime] = Field(None, alias='ExpectedCloseDate')
    AssignedToUserID: Optional[PositiveInt] = Field(None, alias='AssignedToUserID') # CRM User, Foreign Key

    model_config = ConfigDict(populate_by_name=True)

class User(BaseModel): # CRM System User/Sales Rep
    UserID: PositiveInt = Field(..., alias='UserID')
    FirstName: Optional[str] = Field(None, alias='FirstName')
    LastName: Optional[str] = Field(None, alias='LastName')
    Email: Optional[EmailStr] = Field(None, alias='Email')

    model_config = ConfigDict(populate_by_name=True)

# Example Usage (optional, for testing):
# if __name__ == "__main__":
#     contact_data = {
#         "ContactID": 1,
#         "FirstName": "Jane",
#         "LastName": "Doe",
#         "Email": "jane.doe@example.com",
#         "CompanyID": 101
#     }
#     contact = Contact(**contact_data)
#     print("Contact:")
#     print(contact.json(indent=2, by_alias=True))

#     company_data = {
#         "CompanyID": 101,
#         "CompanyName": "Example Corp",
#         "Industry": "Tech",
#         "AnnualRevenue": 1000000.50,
#         "NumberOfEmployees": 50
#     }
#     company = Company(**company_data)
#     print("\nCompany:")
#     print(company.json(indent=2, by_alias=True))

#     interaction_data = {
#         "InteractionID": 1001,
#         "ContactID": 1,
#         "InteractionType": "Email",
#         "InteractionDate": datetime.now(),
#         "Subject": "Follow-up"
#     }
#     interaction = Interaction(**interaction_data)
#     print("\nInteraction:")
#     print(interaction.json(indent=2, by_alias=True))

#     deal_data = {
#         "DealID": 5001,
#         "DealName": "Big Project",
#         "CompanyID": 101,
#         "PrimaryContactID": 1,
#         "Stage": "Proposal",
#         "Amount": 50000.00,
#         "ExpectedCloseDate": datetime.now()
#     }
#     deal = Deal(**deal_data)
#     print("\nDeal:")
#     print(deal.json(indent=2, by_alias=True))

#     user_data = {
#         "UserID": 10,
#         "FirstName": "John",
#         "LastName": "Smith",
#         "Email": "john.smith@example.com"
#     }
#     user = User(**user_data)
#     print("\nUser:")
#     print(user.json(indent=2, by_alias=True))

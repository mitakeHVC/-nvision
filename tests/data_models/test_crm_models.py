import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError
from src.data_models.crm_models import (
    Contact, Company, Interaction, Deal, User
)

# Common data for testing
VALID_DATETIME = datetime.now()
VALID_POSITIVE_INT = 1
ANOTHER_VALID_POSITIVE_INT = 2

# --- Test Contact Model ---
def test_contact_valid_creation_all_fields():
    contact = Contact(
        ContactID=VALID_POSITIVE_INT,
        FirstName="Jane",
        LastName="Doe",
        Email="jane.doe@example.com",
        PhoneNumber="123-456-7890",
        JobTitle="Developer",
        CompanyID=ANOTHER_VALID_POSITIVE_INT,
        LeadSource="Web",
        DateCreated=VALID_DATETIME,
        LastContactedDate=VALID_DATETIME
    )
    assert contact.ContactID == VALID_POSITIVE_INT
    assert contact.FirstName == "Jane"
    assert contact.Email == "jane.doe@example.com"
    assert contact.CompanyID == ANOTHER_VALID_POSITIVE_INT

def test_contact_valid_creation_required_only():
    contact = Contact(ContactID=VALID_POSITIVE_INT)
    assert contact.ContactID == VALID_POSITIVE_INT
    assert contact.FirstName is None
    assert contact.Email is None

def test_contact_contactid_pk_validation():
    with pytest.raises(PydanticValidationError, match="ContactID"):
        Contact(ContactID="invalid")
    with pytest.raises(PydanticValidationError, match="ContactID"):
        Contact(ContactID=0)
    with pytest.raises(PydanticValidationError, match="ContactID"):
        Contact(ContactID=-1)

def test_contact_email_validation():
    with pytest.raises(PydanticValidationError, match="Email"):
        Contact(ContactID=VALID_POSITIVE_INT, Email="not-an-email")
    contact = Contact(ContactID=VALID_POSITIVE_INT, Email="valid.email@example.com")
    assert contact.Email == "valid.email@example.com"

def test_contact_companyid_fk_validation():
    with pytest.raises(PydanticValidationError, match="CompanyID"):
        Contact(ContactID=VALID_POSITIVE_INT, CompanyID=0)
    contact = Contact(ContactID=VALID_POSITIVE_INT, CompanyID=ANOTHER_VALID_POSITIVE_INT)
    assert contact.CompanyID == ANOTHER_VALID_POSITIVE_INT
    contact_none = Contact(ContactID=VALID_POSITIVE_INT, CompanyID=None)
    assert contact_none.CompanyID is None

def test_contact_datetime_validation():
    with pytest.raises(PydanticValidationError, match="DateCreated"):
        Contact(ContactID=VALID_POSITIVE_INT, DateCreated="not-a-datetime")


# --- Test Company Model ---
def test_company_valid_creation_all_fields():
    company = Company(
        CompanyID=VALID_POSITIVE_INT,
        CompanyName="Innovate Corp",
        Industry="Technology",
        Website="http://innovatecorp.com",
        Address="456 Tech Park",
        PhoneNumber="987-654-3210",
        AnnualRevenue=1500000.75,
        NumberOfEmployees=150
    )
    assert company.CompanyID == VALID_POSITIVE_INT
    assert company.CompanyName == "Innovate Corp"
    assert company.AnnualRevenue == 1500000.75
    assert company.NumberOfEmployees == 150

def test_company_valid_creation_required_only():
    company = Company(CompanyID=VALID_POSITIVE_INT)
    assert company.CompanyID == VALID_POSITIVE_INT
    assert company.CompanyName is None

def test_company_companyid_pk_validation():
    with pytest.raises(PydanticValidationError, match="CompanyID"):
        Company(CompanyID=0)

def test_company_annualrevenue_validation():
    with pytest.raises(PydanticValidationError, match="AnnualRevenue"):
        Company(CompanyID=VALID_POSITIVE_INT, AnnualRevenue=-100.0)
    company = Company(CompanyID=VALID_POSITIVE_INT, AnnualRevenue=0.0)
    assert company.AnnualRevenue == 0.0
    company_none = Company(CompanyID=VALID_POSITIVE_INT, AnnualRevenue=None)
    assert company_none.AnnualRevenue is None

def test_company_numberofemployees_validation():
    with pytest.raises(PydanticValidationError, match="NumberOfEmployees"):
        Company(CompanyID=VALID_POSITIVE_INT, NumberOfEmployees=-5)
    company = Company(CompanyID=VALID_POSITIVE_INT, NumberOfEmployees=0)
    assert company.NumberOfEmployees == 0
    company_none = Company(CompanyID=VALID_POSITIVE_INT, NumberOfEmployees=None)
    assert company_none.NumberOfEmployees is None


# --- Test Interaction Model ---
def test_interaction_valid_creation_all_fields():
    interaction = Interaction(
        InteractionID=VALID_POSITIVE_INT,
        ContactID=ANOTHER_VALID_POSITIVE_INT,
        CompanyID=VALID_POSITIVE_INT, # Different from Contact's CompanyID for test variety
        InteractionType="Email",
        InteractionDate=VALID_DATETIME,
        Subject="Follow-up on proposal",
        Notes="Sent email to Jane Doe regarding the new proposal.",
        AssignedToUserID=VALID_POSITIVE_INT + 10
    )
    assert interaction.InteractionID == VALID_POSITIVE_INT
    assert interaction.InteractionType == "Email"
    assert interaction.ContactID == ANOTHER_VALID_POSITIVE_INT

def test_interaction_valid_creation_required_only():
    interaction = Interaction(InteractionID=VALID_POSITIVE_INT)
    assert interaction.InteractionID == VALID_POSITIVE_INT
    assert interaction.ContactID is None

def test_interaction_interactionid_pk_validation():
    with pytest.raises(PydanticValidationError, match="InteractionID"):
        Interaction(InteractionID=0)

def test_interaction_foreign_keys_validation():
    # ContactID
    with pytest.raises(PydanticValidationError, match="ContactID"):
        Interaction(InteractionID=1, ContactID=0)
    # CompanyID
    with pytest.raises(PydanticValidationError, match="CompanyID"):
        Interaction(InteractionID=1, CompanyID=0)
    # AssignedToUserID
    with pytest.raises(PydanticValidationError, match="AssignedToUserID"):
        Interaction(InteractionID=1, AssignedToUserID=0)

    interaction = Interaction(
        InteractionID=1,
        ContactID=VALID_POSITIVE_INT,
        CompanyID=None, # Optional FK
        AssignedToUserID=ANOTHER_VALID_POSITIVE_INT
    )
    assert interaction.ContactID == VALID_POSITIVE_INT
    assert interaction.CompanyID is None
    assert interaction.AssignedToUserID == ANOTHER_VALID_POSITIVE_INT


# --- Test Deal Model ---
def test_deal_valid_creation_all_fields():
    deal = Deal(
        DealID=VALID_POSITIVE_INT,
        DealName="Project Alpha",
        CompanyID=ANOTHER_VALID_POSITIVE_INT,
        PrimaryContactID=VALID_POSITIVE_INT,
        Stage="Negotiation",
        Amount=50000.00,
        ExpectedCloseDate=VALID_DATETIME,
        AssignedToUserID=ANOTHER_VALID_POSITIVE_INT + 1
    )
    assert deal.DealID == VALID_POSITIVE_INT
    assert deal.DealName == "Project Alpha"
    assert deal.Amount == 50000.00

def test_deal_valid_creation_required_only():
    deal = Deal(DealID=VALID_POSITIVE_INT)
    assert deal.DealID == VALID_POSITIVE_INT
    assert deal.DealName is None

def test_deal_dealid_pk_validation():
    with pytest.raises(PydanticValidationError, match="DealID"):
        Deal(DealID=0)

def test_deal_amount_validation():
    with pytest.raises(PydanticValidationError, match="Amount"):
        Deal(DealID=VALID_POSITIVE_INT, Amount=-200.0)
    deal = Deal(DealID=VALID_POSITIVE_INT, Amount=0.0)
    assert deal.Amount == 0.0
    deal_none = Deal(DealID=VALID_POSITIVE_INT, Amount=None)
    assert deal_none.Amount is None

def test_deal_foreign_keys_validation():
    # CompanyID
    with pytest.raises(PydanticValidationError, match="CompanyID"):
        Deal(DealID=1, CompanyID=0)
    # PrimaryContactID
    with pytest.raises(PydanticValidationError, match="PrimaryContactID"):
        Deal(DealID=1, PrimaryContactID=0)
    # AssignedToUserID
    with pytest.raises(PydanticValidationError, match="AssignedToUserID"):
        Deal(DealID=1, AssignedToUserID=0)

    deal = Deal(
        DealID=1,
        CompanyID=VALID_POSITIVE_INT,
        PrimaryContactID=None, # Optional FK
        AssignedToUserID=ANOTHER_VALID_POSITIVE_INT
    )
    assert deal.CompanyID == VALID_POSITIVE_INT
    assert deal.PrimaryContactID is None
    assert deal.AssignedToUserID == ANOTHER_VALID_POSITIVE_INT


# --- Test User Model ---
def test_user_valid_creation_all_fields():
    user = User(
        UserID=VALID_POSITIVE_INT,
        FirstName="John",
        LastName="Smith",
        Email="john.smith@example.com"
    )
    assert user.UserID == VALID_POSITIVE_INT
    assert user.FirstName == "John"
    assert user.Email == "john.smith@example.com"

def test_user_valid_creation_required_only():
    user = User(UserID=VALID_POSITIVE_INT)
    assert user.UserID == VALID_POSITIVE_INT
    assert user.FirstName is None
    assert user.Email is None

def test_user_userid_pk_validation():
    with pytest.raises(PydanticValidationError, match="UserID"):
        User(UserID=0)

def test_user_email_validation():
    with pytest.raises(PydanticValidationError, match="Email"):
        User(UserID=VALID_POSITIVE_INT, Email="invalid-email-format")
    user = User(UserID=VALID_POSITIVE_INT, Email="test.user@company.co.uk")
    assert user.Email == "test.user@company.co.uk"


# --- Generic Data Type Validation Test ---
def test_generic_datatype_validation_crm():
    # Contact.ContactID (PositiveInt)
    with pytest.raises(PydanticValidationError):
        Contact(ContactID="should_be_int")

    # Company.CompanyName (Optional[str])
    with pytest.raises(PydanticValidationError): # Test with a complex type not coercible to str
        Company(CompanyID=1, CompanyName=["Company", "Name"])

    # Deal.Amount (Optional[NonNegativeFloat])
    with pytest.raises(PydanticValidationError):
        Deal(DealID=1, Amount="should_be_float_or_int")

    # User.FirstName (Optional[str])
    user = User(UserID=1, FirstName="123") # Pydantic V2 requires explicit string
    assert user.FirstName == "123"
    with pytest.raises(PydanticValidationError):
        User(UserID=1, FirstName={"name": "test"}) # Cannot coerce dict to str easily

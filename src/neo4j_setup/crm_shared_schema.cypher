// Neo4j Schema for CRM & Shared/Support System Entities
// This file outlines the node labels and their properties as described in
// section 4.1 of the data_schema_and_transformation_proposal.md.
// Data types are harmonized with the Pydantic models in
// src/data_models/crm_models.py and src/data_models/shared_models.py.

// --- CRM System Entities (Nodes) ---

// Node: CRMContact
// Label: CRMContact (using specific label to distinguish from other potential 'Contact' types)
// Properties based on proposal section 4.1 (CRM_Contact Node) and crm_models.Contact:
//   contactID: Integer (Primary Key, from Pydantic Contact.ContactID: PositiveInt)
//   firstName: String (from Pydantic Contact.FirstName: Optional[str])
//   lastName: String (from Pydantic Contact.LastName: Optional[str])
//   email: String (from Pydantic Contact.Email: Optional[EmailStr])
//   phoneNumber: String (from Pydantic Contact.PhoneNumber: Optional[str])
//   jobTitle: String (from Pydantic Contact.JobTitle: Optional[str])
//   leadSource: String (from Pydantic Contact.LeadSource: Optional[str])
//   dateCreated: Datetime (from Pydantic Contact.DateCreated: Optional[datetime])
//   lastContactedDate: Datetime (from Pydantic Contact.LastContactedDate: Optional[datetime])
// Note: Pydantic model Contact.CompanyID (Optional[PositiveInt]) is a foreign key
//       used to establish the :WORKS_FOR relationship with a Company node.

// Node: Company
// Label: Company
// Properties based on proposal section 4.1 (Company Node) and crm_models.Company:
//   companyID: Integer (Primary Key, from Pydantic Company.CompanyID: PositiveInt)
//   companyName: String (from Pydantic Company.CompanyName: Optional[str])
//   industry: String (from Pydantic Company.Industry: Optional[str])
//   website: String (from Pydantic Company.Website: Optional[str])
//   address: String (from Pydantic Company.Address: Optional[str])
//   phoneNumber: String (from Pydantic Company.PhoneNumber: Optional[str])
//   annualRevenue: Float (from Pydantic Company.AnnualRevenue: Optional[NonNegativeFloat])
//   numberOfEmployees: Integer (from Pydantic Company.NumberOfEmployees: Optional[NonNegativeInt])

// Node: Interaction
// Label: Interaction
// Properties based on proposal section 4.1 (Interaction Node) and crm_models.Interaction:
//   interactionID: Integer (Primary Key, from Pydantic Interaction.InteractionID: PositiveInt)
//   interactionType: String (from Pydantic Interaction.InteractionType: Optional[str])
//   interactionDate: Datetime (from Pydantic Interaction.InteractionDate: Optional[datetime])
//   subject: String (from Pydantic Interaction.Subject: Optional[str])
//   notes_summary: String (Proposal 4.1 suggests 'notes_summary'. Pydantic Interaction.Notes: Optional[str] holds full notes. This summary may be a truncated/processed version.)
// Note: Pydantic model Interaction.ContactID, Interaction.CompanyID, and Interaction.AssignedToUserID
//       are foreign keys used for establishing relationships like :PARTICIPATED_IN, :HAS_INTERACTION, :LOGGED.

// Node: Deal
// Label: Deal
// Properties based on proposal section 4.1 (Deal Node) and crm_models.Deal:
//   dealID: Integer (Primary Key, from Pydantic Deal.DealID: PositiveInt)
//   dealName: String (from Pydantic Deal.DealName: Optional[str])
//   stage: String (from Pydantic Deal.Stage: Optional[str])
//   amount: Float (from Pydantic Deal.Amount: Optional[NonNegativeFloat])
//   expectedCloseDate: Datetime (from Pydantic Deal.ExpectedCloseDate: Optional[datetime])
// Note: Pydantic model Deal.CompanyID, Deal.PrimaryContactID, and Deal.AssignedToUserID
//       are foreign keys used for establishing relationships like :ASSOCIATED_WITH, :HAS_PRIMARY_CONTACT, :ASSIGNED_TO.

// Node: User (CRM System User/Sales Rep)
// Label: User
// Properties based on proposal section 4.1 (User Node) and crm_models.User:
//   userID: Integer (Primary Key, from Pydantic User.UserID: PositiveInt)
//   firstName: String (from Pydantic User.FirstName: Optional[str])
//   lastName: String (from Pydantic User.LastName: Optional[str])
//   email: String (from Pydantic User.Email: Optional[EmailStr])

// --- Shared/Support System Entities (Nodes) ---

// Node: ChatSession
// Label: ChatSession
// Properties based on proposal section 4.1 (ChatSession Node) and shared_models.ChatSession:
//   chatSessionID: Integer (Primary Key, from Pydantic ChatSession.ChatSessionID: PositiveInt)
//   startTime: Datetime (from Pydantic ChatSession.StartTime: Optional[datetime])
//   endTime: Datetime (from Pydantic ChatSession.EndTime: Optional[datetime])
//   platform: String (from Pydantic ChatSession.Platform: Optional[str])
// Note: Pydantic model ChatSession.CustomerID, ChatSession.ContactID, ChatSession.UserID
//       are foreign keys used for establishing relationships like :PARTICIPATED_IN_CHAT, :HANDLED_CHAT.

// Node: ChatMessage
// Label: ChatMessage
// Properties based on proposal section 4.1 (ChatMessage Node) and shared_models.ChatMessage:
//   chatMessageID: Integer (Primary Key, from Pydantic ChatMessage.ChatMessageID: PositiveInt)
//   messageText: String (from Pydantic ChatMessage.MessageText: Optional[str]. Proposal 4.1 notes "or summary/embedding ID" - actual content stored here.)
//   timestamp: Datetime (from Pydantic ChatMessage.Timestamp: Optional[datetime])
//   senderType: String (from Pydantic ChatMessage.SenderType: Optional[str])
//   extractedKeywords: List of String (from Pydantic ChatMessage.ExtractedKeywords: Optional[List[str]])
//   classifiedTopics: List of String (from Pydantic ChatMessage.ClassifiedTopics: Optional[List[str]])
// Note: Pydantic model ChatMessage.ChatSessionID and ChatMessage.SenderID
//       are foreign keys used for establishing relationships like :HAS_MESSAGE, :SENT_MESSAGE.

// --- End of Node Schema Definition ---

// --- CRM & Shared System Relationships (Conceptual) ---
// Based on section 4.2 of data_schema_and_transformation_proposal.md.

// --- CRM Relationships ---

// Relationship: WORKS_FOR
// Type: (CRMContact) -[:WORKS_FOR]-> (Company)
// Properties:
//   startDate: Date (Optional, if applicable)
//   endDate: Date (Optional, if applicable)

// Relationship: PARTICIPATED_IN
// Type: (CRMContact) -[:PARTICIPATED_IN]-> (Interaction)
// Properties: None specified in proposal 4.2

// Relationship: HAS_INTERACTION (Company to Interaction)
// Type: (Company) -[:HAS_INTERACTION]-> (Interaction)
// Properties: None specified in proposal 4.2

// Relationship: ASSOCIATED_WITH (Deal to Company)
// Type: (Deal) -[:ASSOCIATED_WITH]-> (Company)
// Properties: None specified in proposal 4.2

// Relationship: HAS_PRIMARY_CONTACT (Deal to CRMContact)
// Type: (Deal) -[:HAS_PRIMARY_CONTACT]-> (CRMContact)
// Properties: None specified in proposal 4.2

// Relationship: INVOLVES_CONTACT (Deal to other CRMContacts)
// Type: (Deal) -[:INVOLVES_CONTACT]-> (CRMContact)
// Properties: None specified in proposal 4.2

// Relationship: ASSIGNED_TO (User to Deal)
// Type: (User) -[:ASSIGNED_TO]-> (Deal)
// Note: Direction can also be (Deal)-[:ASSIGNED_TO]->(User) as per proposal.
// Properties: None specified in proposal 4.2

// Relationship: LOGGED (User to Interaction)
// Type: (User) -[:LOGGED]-> (Interaction)
// Note: Indicates the user who recorded the interaction.
// Properties: None specified in proposal 4.2

// Relationship: OWNS (User to CRMContact - Lead/Contact owner)
// Type: (User) -[:OWNS]-> (CRMContact)
// Properties: None specified in proposal 4.2

// Relationship: OWNS (User to Company - Account owner)
// Type: (User) -[:OWNS]-> (Company)
// Properties: None specified in proposal 4.2

// --- Support System Relationships (Chat) ---

// Relationship: PARTICIPATED_IN_CHAT (ECCustomer to ChatSession)
// Type: (ECCustomer) -[:PARTICIPATED_IN_CHAT]-> (ChatSession)
// Properties: None specified in proposal 4.2

// Relationship: PARTICIPATED_IN_CHAT (CRMContact to ChatSession)
// Type: (CRMContact) -[:PARTICIPATED_IN_CHAT]-> (ChatSession)
// Note: Used if the chat participant is identified as a CRM Contact.
// Properties: None specified in proposal 4.2

// Relationship: HANDLED_CHAT (User to ChatSession)
// Type: (User) -[:HANDLED_CHAT]-> (ChatSession)
// Note: User is a CRM User/Support Agent.
// Properties: None specified in proposal 4.2

// Relationship: HAS_MESSAGE (ChatSession to ChatMessage)
// Type: (ChatSession) -[:HAS_MESSAGE]-> (ChatMessage)
// Properties:
//   sequenceNumber: Integer (Optional, for ordering messages within a session)

// Relationship: SENT_MESSAGE (ECCustomer to ChatMessage)
// Type: (ECCustomer) -[:SENT_MESSAGE]-> (ChatMessage)
// Properties: None specified in proposal 4.2
// Note: The proposal `(CUSTOMER|USER) --SENT_MESSAGE--> CHAT_MESSAGE` is split.
//       Alternatively, a single :SENT_MESSAGE type with a property on the relationship,
//       or relying on ChatMessage.SenderType and ChatMessage.SenderID, could model this.

// Relationship: SENT_MESSAGE (User to ChatMessage)
// Type: (User) -[:SENT_MESSAGE]-> (ChatMessage)
// Properties: None specified in proposal 4.2

// --- Cross-System Relationships ---

// Relationship: IS_SAME_AS (Identity Link)
// Type: (ECCustomer) -[:IS_SAME_AS]-> (CRMContact)
// Properties:
//   confidenceScore: Float (Indicates the confidence of the identity match)

// Relationship: IS_LINKED_TO (ECCustomer to Company)
// Type: (ECCustomer) -[:IS_LINKED_TO]-> (Company)
// Note: For B2B customers or other explicit links.
// Properties: None specified in proposal 4.2

// Relationship: INITIATED_FROM_INTERACTION (Order to Interaction)
// Type: (Order) -[:INITIATED_FROM_INTERACTION]-> (Interaction)
// Note: E.g., an order placed after a sales call logged as an Interaction.
// Properties: None specified in proposal 4.2

// Relationship: MENTIONED_IN (Product to Interaction)
// Type: (Product) -[:MENTIONED_IN]-> (Interaction)
// Properties:
//   mentionCount: Integer (Optional, how many times product mentioned)

// --- End of Relationship Schema Definition ---

// --- CRM & Shared System Constraints and Indexes ---
// These are runnable Cypher commands.
// Use `IF NOT EXISTS` for idempotency.

// Unique Constraints for Primary Keys:
CREATE CONSTRAINT IF NOT EXISTS FOR (c:CRMContact) REQUIRE c.contactID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (co:Company) REQUIRE co.companyID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interaction) REQUIRE i.interactionID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Deal) REQUIRE d.dealID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.userID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cs:ChatSession) REQUIRE cs.chatSessionID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cm:ChatMessage) REQUIRE cm.chatMessageID IS UNIQUE;

// Indexes for Frequently Queried Properties:
CREATE INDEX IF NOT EXISTS FOR (c:CRMContact) ON (c.email);
CREATE INDEX IF NOT EXISTS FOR (co:Company) ON (co.companyName);
CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.email);
CREATE INDEX IF NOT EXISTS FOR (cs:ChatSession) ON (cs.platform);
CREATE INDEX IF NOT EXISTS FOR (cm:ChatMessage) ON (cm.timestamp);
CREATE INDEX IF NOT EXISTS FOR (cm:ChatMessage) ON (cm.senderType); // Added senderType as it's often filtered

// --- End of CRM & Shared System Constraints and Indexes ---
